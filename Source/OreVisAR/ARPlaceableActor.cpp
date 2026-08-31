// Copyright OreVis. Licensed under MIT.

#include "ARPlaceableActor.h"

#include "ARBlueprintLibrary.h"
#include "ARPin.h"
#include "ARTypes.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "OreVisAR.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	constexpr float PinRetryDelaySeconds = 0.35f;
}

AARPlaceableActor::AARPlaceableActor()
{
	PrimaryActorTick.bCanEverTick = false;

	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	RootComponent = Mesh;
	Mesh->SetCollisionProfileName(TEXT("BlockAllDynamic"));
	Mesh->SetGenerateOverlapEvents(false);
	Mesh->SetMobility(EComponentMobility::Movable);
	// Explicitly disable physics so nothing shoves a placed object once the
	// AR pin has taken responsibility for its transform.
	Mesh->SetSimulatePhysics(false);
	Mesh->SetEnableGravity(false);

	// Default to the engine's cube so the class is usable without Blueprint
	// subclassing. Designers can override via a BP child.
	static ConstructorHelpers::FObjectFinder<UStaticMesh> CubeMesh(
		TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (CubeMesh.Succeeded())
	{
		Mesh->SetStaticMesh(CubeMesh.Object);
		Mesh->SetRelativeScale3D(FVector(0.25f));
	}

	Tags.Add(FName(TEXT("ARPlaceable")));
}

void AARPlaceableActor::BeginPlay()
{
	Super::BeginPlay();

	if (Mesh && Mesh->GetMaterial(0))
	{
		HighlightMID = Mesh->CreateAndSetMaterialInstanceDynamic(0);
	}

	// Attempt to anchor immediately. If AR tracking is not yet Running the
	// call schedules a retry, so callers don't need to know the session state.
	PinToARWorld();
}

void AARPlaceableActor::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (UWorld* World = GetWorld())
	{
		World->GetTimerManager().ClearTimer(PinRetryHandle);
	}
	UnpinFromARWorld();
	Super::EndPlay(EndPlayReason);
}

void AARPlaceableActor::SetGrabbed(bool bGrabbed)
{
	if (bIsGrabbed == bGrabbed)
	{
		return;
	}
	bIsGrabbed = bGrabbed;

	if (bGrabbed)
	{
		// Free the mesh from its AR pin so the pawn can move it. Otherwise
		// the pin's per-frame transform update would fight SetActorLocation.
		UnpinFromARWorld();
	}
	else
	{
		// Freeze the new resting place to real-world features.
		PinToARWorld();
	}

	if (HighlightMID)
	{
		// Tint the object while grabbed so the user gets clear feedback
		// through the glasses.
		const FLinearColor Tint = bGrabbed ? FLinearColor(1.2f, 0.8f, 0.2f)
		                                   : FLinearColor::White;
		HighlightMID->SetVectorParameterValue(TEXT("Tint"), Tint);
	}
}

void AARPlaceableActor::ApplyPinchScale(float ScaleDelta)
{
	if (FMath::IsNearlyZero(ScaleDelta))
	{
		return;
	}
	const FVector Current = GetActorScale3D();
	const float NewUniform = FMath::Clamp(Current.X * ScaleDelta, MinScale, MaxScale);
	SetActorScale3D(FVector(NewUniform));
}

bool AARPlaceableActor::PinToARWorld()
{
	if (!Mesh)
	{
		return false;
	}

	// Cancel any existing pin before creating a new one so we don't leak
	// anchors into the AR session.
	UnpinFromARWorld();

	const FARSessionStatus Status = UARBlueprintLibrary::GetARSessionStatus();
	if (Status.Status != EARSessionStatus::Running)
	{
		// Retry once the AR session has come up. This is the common case
		// for scatter-spawned objects created before tracking is stable.
		if (UWorld* World = GetWorld())
		{
			World->GetTimerManager().SetTimer(PinRetryHandle,
				FTimerDelegate::CreateWeakLambda(this, [this]() { PinToARWorld(); }),
				PinRetryDelaySeconds, false);
		}
		return false;
	}

	AnchorPin = UARBlueprintLibrary::PinComponent(Mesh, GetActorTransform(),
	                                              /*TrackedGeometry*/ nullptr,
	                                              GetFName());
	if (!AnchorPin)
	{
		UE_LOG(LogOreVisAR, Warning,
			TEXT("AARPlaceableActor::PinToARWorld: PinComponent returned null for %s."),
			*GetName());
		return false;
	}
	return true;
}

void AARPlaceableActor::UnpinFromARWorld()
{
	if (UWorld* World = GetWorld())
	{
		World->GetTimerManager().ClearTimer(PinRetryHandle);
	}
	if (AnchorPin)
	{
		UARBlueprintLibrary::RemovePin(AnchorPin);
		AnchorPin = nullptr;
	}
}
