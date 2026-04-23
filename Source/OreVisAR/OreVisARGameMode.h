// Copyright OreVis. Licensed under MIT.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "OreVisARGameMode.generated.h"

class AARPlaceableActor;
class AOreVisARPawn;

/**
 * Game mode that spawns an initial set of AR placeables around the player
 * and tracks the placement radius used for clamping.
 */
UCLASS(Config = Game)
class OREVISAR_API AOreVisARGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AOreVisARGameMode();

	virtual void StartPlay() override;

	/** Radius (cm) in which initial objects are scattered. */
	UPROPERTY(Config, EditAnywhere, BlueprintReadWrite, Category = "AR")
	float MaxPlacementRadiusCm = 1000.0f;

	/** Number of objects to spawn when the session starts. */
	UPROPERTY(Config, EditAnywhere, BlueprintReadWrite, Category = "AR")
	int32 InitialObjectCount = 3;

	/** Class used for auto-spawned objects. Override in a BP subclass. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AR")
	TSubclassOf<AARPlaceableActor> PlaceableClass;

protected:
	void ScatterInitialObjects(AOreVisARPawn* Pawn);
};
