// Copyright OreVis. Licensed under MIT.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "OreVisARGameMode.generated.h"

class AARPlaceableActor;
class AOreVisARPawn;
class UARSpawnButtonWidget;
class UStartupTachoWidget;
class UUserWidget;

/**
 * Game mode that owns AR session config (radius, object count, classes) and
 * lazily scatters objects once the pawn reports that tracking is live.
 * Also instantiates the sample HUD widgets: startup tachos + spawn button.
 */
UCLASS(Config = Game)
class OREVISAR_API AOreVisARGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AOreVisARGameMode();

	virtual void StartPlay() override;

	/** Scatter `InitialObjectCount` placeables around the pawn. */
	UFUNCTION(BlueprintCallable, Category = "AR")
	void ScatterInitialObjects(AOreVisARPawn* Pawn);

	/** Radius (cm) used for initial spawn scatter and runtime clamping. */
	UPROPERTY(Config, EditAnywhere, BlueprintReadWrite, Category = "AR")
	float MaxPlacementRadiusCm = 1000.0f;

	/** Number of objects to spawn when tracking first goes live. */
	UPROPERTY(Config, EditAnywhere, BlueprintReadWrite, Category = "AR")
	int32 InitialObjectCount = 3;

	/** Class used for auto-spawned / button-spawned objects. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AR")
	TSubclassOf<AARPlaceableActor> PlaceableClass;

	/** Startup tacho widget shown from 0→100% during boot. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AR|HUD")
	TSubclassOf<UStartupTachoWidget> StartupTachoWidgetClass;

	/** Second tacho instance — optional. Same class, different anchor point. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AR|HUD")
	TSubclassOf<UStartupTachoWidget> SecondaryTachoWidgetClass;

	/** Tap-to-spawn HUD button shown after startup completes. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AR|HUD")
	TSubclassOf<UARSpawnButtonWidget> SpawnButtonWidgetClass;

protected:
	void CreateHUDWidgets();

	UPROPERTY() TObjectPtr<UUserWidget> StartupTachoWidget;
	UPROPERTY() TObjectPtr<UUserWidget> SecondaryTachoWidget;
	UPROPERTY() TObjectPtr<UUserWidget> SpawnButtonWidget;
};
