// Copyright OreVis. Licensed under MIT.

#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "OreVisStartupSubsystem.h"
#include "StartupTachoWidget.generated.h"

class UProgressBar;
class UTextBlock;
class UImage;

/**
 * Sample tachometer-style HUD widget showing AR startup progress from 0→100%.
 *
 * Designers create a Blueprint child (e.g. `WBP_StartupTacho`) with any of:
 *   - a `UProgressBar`  named `ProgressBar`   — auto-driven linear fill
 *   - a `UTextBlock`    named `StageLabel`    — current stage name
 *   - a `UTextBlock`    named `PercentLabel`  — "42%"
 *   - a `UImage`        named `TachoImage`    — its material's `Progress` scalar
 *                                               parameter is driven for radial
 *                                               gauges
 *
 * Any subset may be bound (all are optional). For fully custom visuals, hook
 * the `OnTachoProgressUpdated` BlueprintImplementableEvent and drive widgets
 * yourself.
 */
UCLASS()
class OREVISAR_API UStartupTachoWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	/** Name of the scalar parameter on the `TachoImage` material to drive. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "OreVis|Tacho")
	FName TachoProgressParam = TEXT("Progress");

	/** If true, the widget auto-hides once progress reaches 100%. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "OreVis|Tacho")
	bool bHideWhenReady = true;

	/** Seconds to wait after reaching 100% before hiding. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "OreVis|Tacho",
		meta = (ClampMin = "0.0"))
	float HideDelaySeconds = 0.75f;

protected:
	virtual void NativeConstruct() override;
	virtual void NativeDestruct() override;

	/** Drive custom visuals (radial masks, etc.) from Blueprint. */
	UFUNCTION(BlueprintImplementableEvent, Category = "OreVis|Tacho")
	void OnTachoProgressUpdated(float Progress01, EOreVisStartupStage Stage);

	UPROPERTY(meta = (BindWidgetOptional))
	TObjectPtr<UProgressBar> ProgressBar;

	UPROPERTY(meta = (BindWidgetOptional))
	TObjectPtr<UTextBlock> StageLabel;

	UPROPERTY(meta = (BindWidgetOptional))
	TObjectPtr<UTextBlock> PercentLabel;

	UPROPERTY(meta = (BindWidgetOptional))
	TObjectPtr<UImage> TachoImage;

private:
	UFUNCTION()
	void HandleProgressChanged(float Progress01, EOreVisStartupStage Stage);

	void ApplyProgress(float Progress01, EOreVisStartupStage Stage);

	FTimerHandle HideTimerHandle;
};
