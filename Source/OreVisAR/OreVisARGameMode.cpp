// Copyright OreVis. Licensed under MIT.

#include "OreVisARGameMode.h"

#include "ARPlaceableActor.h"
#include "ARSpawnButtonWidget.h"
#include "Blueprint/UserWidget.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "OreVisAR.h"
#include "OreVisARPawn.h"
#include "StartupTachoWidget.h"

AOreVisARGameMode::AOreVisARGameMode()
{
	DefaultPawnClass = AOreVisARPawn::StaticClass();
	PlaceableClass = AARPlaceableActor::StaticClass();
}

void AOreVisARGameMode::StartPlay()
{
	Super::StartPlay();

	APlayerController* PC = GetWorld()->GetFirstPlayerController();
	AOreVisARPawn* Pawn = PC ? Cast<AOreVisARPawn>(PC->GetPawn()) : nullptr;
	if (Pawn)
	{
		// Keep the pawn's clamp radius in sync with the game mode config.
		Pawn->MaxPlacementRadiusCm = MaxPlacementRadiusCm;
	}
	else
	{
		UE_LOG(LogOreVisAR, Warning, TEXT("StartPlay: no OreVisARPawn found."));
	}

	CreateHUDWidgets();
	// Note: scatter is deferred — the pawn triggers ScatterInitialObjects()
	// once `EARSessionStatus::Running` is reported so we don't spawn objects
	// into an un-tracked world.
}

void AOreVisARGameMode::ScatterInitialObjects(AOreVisARPawn* Pawn)
{
	if (!Pawn || !PlaceableClass || InitialObjectCount <= 0)
	{
		return;
	}

	const FVector Origin = Pawn->GetActorLocation();
	const FRotator PawnRot = Pawn->GetActorRotation();

	for (int32 i = 0; i < InitialObjectCount; ++i)
	{
		const float Yaw = FMath::FRandRange(-60.f, 60.f);
		const float Pitch = FMath::FRandRange(-10.f, 15.f);
		const float Distance = FMath::FRandRange(150.f, MaxPlacementRadiusCm * 0.7f);

		const FRotator Offset = PawnRot + FRotator(Pitch, Yaw, 0.f);
		const FVector Location = Origin + Offset.Vector() * Distance;

		FActorSpawnParameters Params;
		Params.SpawnCollisionHandlingOverride =
			ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
		GetWorld()->SpawnActor<AARPlaceableActor>(PlaceableClass, Location,
			FRotator::ZeroRotator, Params);
	}

	UE_LOG(LogOreVisAR, Log, TEXT("Scattered %d AR placeables within %.0fcm."),
		InitialObjectCount, MaxPlacementRadiusCm);
}

void AOreVisARGameMode::CreateHUDWidgets()
{
	APlayerController* PC = GetWorld()->GetFirstPlayerController();
	if (!PC)
	{
		return;
	}

	if (StartupTachoWidgetClass)
	{
		StartupTachoWidget = CreateWidget<UUserWidget>(PC, StartupTachoWidgetClass);
		if (StartupTachoWidget) { StartupTachoWidget->AddToViewport(10); }
	}
	if (SecondaryTachoWidgetClass)
	{
		SecondaryTachoWidget = CreateWidget<UUserWidget>(PC, SecondaryTachoWidgetClass);
		if (SecondaryTachoWidget) { SecondaryTachoWidget->AddToViewport(10); }
	}
	if (SpawnButtonWidgetClass)
	{
		SpawnButtonWidget = CreateWidget<UUserWidget>(PC, SpawnButtonWidgetClass);
		if (SpawnButtonWidget) { SpawnButtonWidget->AddToViewport(5); }
	}
}
