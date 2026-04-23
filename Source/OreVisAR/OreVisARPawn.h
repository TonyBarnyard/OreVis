// Copyright OreVis. Licensed under MIT.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "OreVisARPawn.generated.h"

class UCameraComponent;
class UInputAction;
class UInputMappingContext;
class UARSessionConfig;
class AARPlaceableActor;
class UOreVisStartupSubsystem;
struct FInputActionValue;

/**
 * Player pawn for the AR session.
 *
 * Owns the XR camera (fed by the phone pose + XREAL IMU via OpenXR on-device,
 * or by the Android ARCore passthrough camera when the glasses are not
 * attached) and routes touchscreen pinch + drag into object manipulation.
 *
 * Input model on the Samsung S24 touchscreen:
 *   - Single finger down on an AR object  -> grab it
 *   - Single finger drag                    -> move the grabbed object along the
 *                                              camera view plane, clamped to
 *                                              MaxPlacementRadiusCm from the pawn
 *   - Two-finger pinch                      -> scale the grabbed object
 *   - Single finger up                      -> release
 */
UCLASS()
class OREVISAR_API AOreVisARPawn : public APawn
{
	GENERATED_BODY()

public:
	AOreVisARPawn();

	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	virtual void Tick(float DeltaSeconds) override;
	virtual void SetupPlayerInputComponent(UInputComponent* InputComponent) override;

	/** Maximum radius (cm) the user can drag an object away from themselves. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AR",
		meta = (ClampMin = "50", ClampMax = "5000"))
	float MaxPlacementRadiusCm = 1000.0f;

	/** AR session descriptor used to start tracking at BeginPlay. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AR")
	TObjectPtr<UARSessionConfig> ARConfig;

	// ------ Enhanced Input assets (assign in BP child) --------------------
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AR|Input")
	TObjectPtr<UInputMappingContext> InputMapping;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AR|Input")
	TObjectPtr<UInputAction> IA_Touch;      // 1D axis: 1.0 while pressed

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AR|Input")
	TObjectPtr<UInputAction> IA_TouchMove;  // 2D axis: normalized screen delta

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AR|Input")
	TObjectPtr<UInputAction> IA_Pinch;      // 1D axis: pinch scale delta

	/**
	 * Spawn a new placeable at `DistanceCm` along the camera's forward axis.
	 * If `ClassOverride` is null, asks the game mode for the default class.
	 * Called by the `ARSpawnButtonWidget` sample HUD.
	 */
	UFUNCTION(BlueprintCallable, Category = "AR")
	AARPlaceableActor* SpawnPlaceableInFront(float DistanceCm = 200.0f,
		TSubclassOf<AARPlaceableActor> ClassOverride = nullptr);

protected:
	UPROPERTY(VisibleAnywhere, Category = "AR")
	TObjectPtr<UCameraComponent> Camera;

private:
	void HandleTouchStarted(const FInputActionValue& Value);
	void HandleTouchEnded(const FInputActionValue& Value);
	void HandleTouchMove(const FInputActionValue& Value);
	void HandlePinch(const FInputActionValue& Value);

	AARPlaceableActor* TraceForPlaceable() const;
	void MoveGrabbedAlongView(FVector2D ScreenDelta);
	void ClampToPlacementRadius(AActor* Target) const;

	UPROPERTY()
	TObjectPtr<AARPlaceableActor> Grabbed;

	/** Cached distance from pawn to the grabbed object at grab-time. */
	float GrabDistance = 100.0f;

	/** Set once AR tracking has gone live and the initial scatter has run. */
	bool bInitialSpawnComplete = false;
};
