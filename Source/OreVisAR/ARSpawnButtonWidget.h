// Copyright OreVis. Licensed under MIT.

#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "ARSpawnButtonWidget.generated.h"

class UButton;
class AARPlaceableActor;

/**
 * Sample on-screen button: tap to spawn a new AR placeable ~SpawnDistanceCm
 * in front of the user. The designer creates a BP child with a UButton
 * named `SpawnButton` — the click handler is hooked in native code.
 */
UCLASS()
class OREVISAR_API UARSpawnButtonWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	/** Distance in front of the pawn at which new objects appear. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AR|Spawn",
		meta = (ClampMin = "50.0", ClampMax = "5000.0"))
	float SpawnDistanceCm = 200.0f;

	/** Override class to spawn. If null, falls back to the game mode's default. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AR|Spawn")
	TSubclassOf<AARPlaceableActor> SpawnClassOverride;

protected:
	virtual void NativeConstruct() override;
	virtual void NativeDestruct() override;

	UPROPERTY(meta = (BindWidgetOptional))
	TObjectPtr<UButton> SpawnButton;

private:
	UFUNCTION()
	void HandleSpawnClicked();
};
