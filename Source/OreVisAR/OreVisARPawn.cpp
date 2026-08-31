// Copyright OreVis. Licensed under MIT.

#include "OreVisARPawn.h"

#include "ARPlaceableActor.h"
#include "ARBlueprintLibrary.h"
#include "ARSessionConfig.h"
#include "ARTypes.h"
#include "Camera/CameraComponent.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "Engine/World.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "InputActionValue.h"
#include "OreVisAR.h"
#include "OreVisARGameMode.h"
#include "OreVisStartupSubsystem.h"

AOreVisARPawn::AOreVisARPawn()
{
	PrimaryActorTick.bCanEverTick = true;

	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	RootComponent = Camera;
	Camera->bLockToHmd = true;              // Use OpenXR / HMD pose when present
	Camera->SetRelativeLocation(FVector::ZeroVector);

	bUseControllerRotationYaw = false;
	bUseControllerRotationPitch = false;
	bUseControllerRotationRoll = false;
}

void AOreVisARPawn::BeginPlay()
{
	Super::BeginPlay();

	UOreVisStartupSubsystem* Startup = UOreVisStartupSubsystem::Get(this);

	if (ARConfig)
	{
		if (Startup) { Startup->SetStage(EOreVisStartupStage::StartingARSession); }
		UARBlueprintLibrary::StartARSession(ARConfig);
		if (Startup) { Startup->SetStage(EOreVisStartupStage::WaitingForTracking); }
	}
	else
	{
		UE_LOG(LogOreVisAR, Warning,
			TEXT("AOreVisARPawn has no ARSessionConfig assigned — AR session not started."));
		if (Startup) { Startup->ForceStage(EOreVisStartupStage::Failed); }
	}

	if (APlayerController* PC = Cast<APlayerController>(GetController()))
	{
		PC->bShowMouseCursor = false;
		PC->bEnableTouchEvents = true;
		PC->bEnableTouchOverEvents = true;

		if (ULocalPlayer* LP = PC->GetLocalPlayer())
		{
			if (UEnhancedInputLocalPlayerSubsystem* Subsys =
					LP->GetSubsystem<UEnhancedInputLocalPlayerSubsystem>())
			{
				if (InputMapping)
				{
					Subsys->AddMappingContext(InputMapping, 0);
				}
			}
		}
	}
}

void AOreVisARPawn::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	UARBlueprintLibrary::StopARSession();
	Super::EndPlay(EndPlayReason);
}

void AOreVisARPawn::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	// Wait for AR tracking to go live, then bump the startup tacho through
	// the scatter → ready transition and let the game mode drop the initial
	// objects. Runs once per session; tick self-disables afterwards so we
	// don't fight AR pin updates on every placeable each frame.
	if (bInitialSpawnComplete)
	{
		return;
	}

	const EARSessionStatus Status = UARBlueprintLibrary::GetARSessionStatus().Status;
	if (Status != EARSessionStatus::Running)
	{
		return;
	}

	UOreVisStartupSubsystem* Startup = UOreVisStartupSubsystem::Get(this);
	if (Startup) { Startup->SetStage(EOreVisStartupStage::ScatteringObjects); }

	if (AOreVisARGameMode* GM = GetWorld()->GetAuthGameMode<AOreVisARGameMode>())
	{
		GM->ScatterInitialObjects(this);
	}

	if (Startup) { Startup->SetStage(EOreVisStartupStage::Ready); }
	bInitialSpawnComplete = true;
	SetActorTickEnabled(false);
}

AARPlaceableActor* AOreVisARPawn::SpawnPlaceableInFront(float DistanceCm,
	TSubclassOf<AARPlaceableActor> ClassOverride)
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return nullptr;
	}

	TSubclassOf<AARPlaceableActor> Class = ClassOverride;
	if (!Class)
	{
		if (AOreVisARGameMode* GM = World->GetAuthGameMode<AOreVisARGameMode>())
		{
			Class = GM->PlaceableClass;
		}
	}
	if (!Class)
	{
		Class = AARPlaceableActor::StaticClass();
	}

	const float ClampedDistance = FMath::Clamp(DistanceCm, 50.0f, MaxPlacementRadiusCm);
	const FVector CamLoc = Camera ? Camera->GetComponentLocation() : GetActorLocation();
	const FVector Forward = Camera ? Camera->GetForwardVector() : GetActorForwardVector();
	const FVector SpawnLoc = CamLoc + Forward * ClampedDistance;

	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride =
		ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
	return World->SpawnActor<AARPlaceableActor>(Class, SpawnLoc, FRotator::ZeroRotator, Params);
}

void AOreVisARPawn::SetupPlayerInputComponent(UInputComponent* InputComp)
{
	Super::SetupPlayerInputComponent(InputComp);

	if (UEnhancedInputComponent* EIC = Cast<UEnhancedInputComponent>(InputComp))
	{
		if (IA_Touch)
		{
			EIC->BindAction(IA_Touch, ETriggerEvent::Started,   this, &AOreVisARPawn::HandleTouchStarted);
			EIC->BindAction(IA_Touch, ETriggerEvent::Completed, this, &AOreVisARPawn::HandleTouchEnded);
			EIC->BindAction(IA_Touch, ETriggerEvent::Canceled,  this, &AOreVisARPawn::HandleTouchEnded);
		}
		if (IA_TouchMove)
		{
			EIC->BindAction(IA_TouchMove, ETriggerEvent::Triggered, this, &AOreVisARPawn::HandleTouchMove);
		}
		if (IA_Pinch)
		{
			EIC->BindAction(IA_Pinch, ETriggerEvent::Triggered, this, &AOreVisARPawn::HandlePinch);
		}
	}
}

// ---------------------------------------------------------------------------
// Input handlers
// ---------------------------------------------------------------------------

void AOreVisARPawn::HandleTouchStarted(const FInputActionValue& /*Value*/)
{
	if (AARPlaceableActor* Hit = TraceForPlaceable())
	{
		Grabbed = Hit;
		GrabDistance = FVector::Dist(Camera->GetComponentLocation(),
		                             Hit->GetActorLocation());
		Hit->SetGrabbed(true);
	}
}

void AOreVisARPawn::HandleTouchEnded(const FInputActionValue& /*Value*/)
{
	if (Grabbed)
	{
		Grabbed->SetGrabbed(false);
		Grabbed = nullptr;
	}
}

void AOreVisARPawn::HandleTouchMove(const FInputActionValue& Value)
{
	if (!Grabbed)
	{
		return;
	}
	MoveGrabbedAlongView(Value.Get<FVector2D>());
}

void AOreVisARPawn::HandlePinch(const FInputActionValue& Value)
{
	if (!Grabbed)
	{
		return;
	}
	// Convert a small per-frame delta into a multiplicative factor close to 1.
	const float Delta = Value.Get<float>();
	Grabbed->ApplyPinchScale(1.0f + Delta);
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

AARPlaceableActor* AOreVisARPawn::TraceForPlaceable() const
{
	APlayerController* PC = Cast<APlayerController>(GetController());
	if (!PC)
	{
		return nullptr;
	}

	float TouchX = 0.f, TouchY = 0.f;
	bool bPressed = false;
	PC->GetInputTouchState(ETouchIndex::Touch1, TouchX, TouchY, bPressed);

	FVector WorldOrigin, WorldDir;
	if (!PC->DeprojectScreenPositionToWorld(TouchX, TouchY, WorldOrigin, WorldDir))
	{
		return nullptr;
	}

	FHitResult Hit;
	const FVector End = WorldOrigin + WorldDir * MaxPlacementRadiusCm;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(OreVisARPinch), /*bTraceComplex*/ false, this);
	if (GetWorld()->LineTraceSingleByChannel(Hit, WorldOrigin, End, ECC_Visibility, Params))
	{
		return Cast<AARPlaceableActor>(Hit.GetActor());
	}
	return nullptr;
}

void AOreVisARPawn::MoveGrabbedAlongView(FVector2D ScreenDelta)
{
	APlayerController* PC = Cast<APlayerController>(GetController());
	if (!PC || !Grabbed)
	{
		return;
	}

	float TouchX = 0.f, TouchY = 0.f;
	bool bPressed = false;
	PC->GetInputTouchState(ETouchIndex::Touch1, TouchX, TouchY, bPressed);

	FVector WorldOrigin, WorldDir;
	if (!PC->DeprojectScreenPositionToWorld(TouchX, TouchY, WorldOrigin, WorldDir))
	{
		return;
	}

	// Keep the object at its original grab distance so drag feels like
	// pushing the object around on an arc in front of the user.
	const FVector NewLocation = WorldOrigin + WorldDir * GrabDistance;
	Grabbed->SetActorLocation(NewLocation, /*bSweep*/ false);
	ClampToPlacementRadius(Grabbed);
}

void AOreVisARPawn::ClampToPlacementRadius(AActor* Target) const
{
	if (!Target)
	{
		return;
	}
	const FVector PawnLoc = GetActorLocation();
	const FVector Offset = Target->GetActorLocation() - PawnLoc;
	const float DistSq = Offset.SizeSquared();
	const float MaxSq = MaxPlacementRadiusCm * MaxPlacementRadiusCm;
	if (DistSq > MaxSq)
	{
		const FVector Clamped = PawnLoc + Offset.GetSafeNormal() * MaxPlacementRadiusCm;
		Target->SetActorLocation(Clamped);
	}
}
