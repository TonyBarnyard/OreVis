// Copyright OreVis. Licensed under MIT.

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "OreVisStartupSubsystem.generated.h"

/**
 * Discrete stages that the AR session passes through on its way to "Ready".
 * Each stage maps to a fixed 0–100% bucket used to drive the startup tachos.
 */
UENUM(BlueprintType)
enum class EOreVisStartupStage : uint8
{
	NotStarted          UMETA(DisplayName = "Not Started"),           // 0%
	LoadingAssets       UMETA(DisplayName = "Loading Assets"),        // 10%
	StartingARSession   UMETA(DisplayName = "Starting AR Session"),   // 25%
	WaitingForTracking  UMETA(DisplayName = "Waiting For Tracking"),  // 50%
	ScatteringObjects   UMETA(DisplayName = "Placing Objects"),       // 75%
	Ready               UMETA(DisplayName = "Ready"),                 // 100%
	Failed              UMETA(DisplayName = "Failed")                 // 0% (error)
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(
	FOnOreVisStartupProgressChanged,
	float, Progress01,
	EOreVisStartupStage, Stage);

/**
 * Broadcasts startup progress (0..1) as the AR app boots.
 * Widgets bind to OnProgressChanged to render tachometer-style gauges.
 */
UCLASS()
class OREVISAR_API UOreVisStartupSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;

	/** Jump to a specific stage; idempotent — no-op if already at (or past) it. */
	UFUNCTION(BlueprintCallable, Category = "OreVis|Startup")
	void SetStage(EOreVisStartupStage NewStage);

	/** Force a stage regardless of ordering (use for error transitions). */
	UFUNCTION(BlueprintCallable, Category = "OreVis|Startup")
	void ForceStage(EOreVisStartupStage NewStage);

	UFUNCTION(BlueprintPure, Category = "OreVis|Startup")
	float GetProgress01() const { return CachedProgress; }

	UFUNCTION(BlueprintPure, Category = "OreVis|Startup")
	int32 GetProgressPercent() const { return FMath::RoundToInt(CachedProgress * 100.f); }

	UFUNCTION(BlueprintPure, Category = "OreVis|Startup")
	EOreVisStartupStage GetStage() const { return CurrentStage; }

	UFUNCTION(BlueprintPure, Category = "OreVis|Startup")
	FText GetStageLabel() const;

	UPROPERTY(BlueprintAssignable, Category = "OreVis|Startup")
	FOnOreVisStartupProgressChanged OnProgressChanged;

	/** Convenience lookup for widgets placed in levels. */
	static UOreVisStartupSubsystem* Get(const UObject* WorldContext);

private:
	static float ProgressForStage(EOreVisStartupStage Stage);
	void BroadcastCurrent();

	EOreVisStartupStage CurrentStage = EOreVisStartupStage::NotStarted;
	float CachedProgress = 0.0f;
};
