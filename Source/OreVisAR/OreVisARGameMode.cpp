// Copyright OreVis. Licensed under MIT.

#include "OreVisARGameMode.h"

#include "ARPlaceableActor.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "OreVisAR.h"
#include "OreVisARPawn.h"

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
	if (!Pawn)
	{
		UE_LOG(LogOreVisAR, Warning, TEXT("StartPlay: no OreVisARPawn found; skipping scatter."));
		return;
	}

	// Keep the pawn's clamp radius in sync with the game mode config so a
	// single value drives both spawn scatter and runtime clamping.
	Pawn->MaxPlacementRadiusCm = MaxPlacementRadiusCm;
	ScatterInitialObjects(Pawn);
}

void AOreVisARGameMode::ScatterInitialObjects(AOreVisARPawn* Pawn)
{
	if (!PlaceableClass || InitialObjectCount <= 0)
	{
		return;
	}

	const FVector Origin = Pawn->GetActorLocation();
	const FRotator PawnRot = Pawn->GetActorRotation();

	// Spread objects in a forward-biased arc so they land in the user's
	// field of view when the session starts.
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
		GetWorld()->SpawnActor<AARPlaceableActor>(PlaceableClass, Location, FRotator::ZeroRotator, Params);
	}

	UE_LOG(LogOreVisAR, Log, TEXT("Scattered %d AR placeables within %.0fcm."),
		InitialObjectCount, MaxPlacementRadiusCm);
}
