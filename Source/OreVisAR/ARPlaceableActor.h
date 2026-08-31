// Copyright OreVis. Licensed under MIT.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ARPlaceableActor.generated.h"

class UStaticMeshComponent;
class UMaterialInstanceDynamic;
class UARPin;

/**
 * A 3D object the user can place, pinch-select, and drag around the AR world.
 * Spawned by the AR game mode within a fixed radius of the player.
 *
 * Placement is held to real-world features via an ARPin created through the
 * AR Framework. The pin is dropped whenever the object comes to rest and
 * removed while the user is actively dragging it, so ARCore's per-frame
 * drift correction keeps the object visually anchored without fighting user
 * input.
 */
UCLASS()
class OREVISAR_API AARPlaceableActor : public AActor
{
	GENERATED_BODY()

public:
	AARPlaceableActor();

	/** Called by the pawn when the object is grabbed / released. */
	UFUNCTION(BlueprintCallable, Category = "AR|Placeable")
	void SetGrabbed(bool bGrabbed);

	/** True while the user is actively moving this object. */
	UFUNCTION(BlueprintPure, Category = "AR|Placeable")
	bool IsGrabbed() const { return bIsGrabbed; }

	/** Uniform scale applied by a pinch gesture. Clamped to [MinScale, MaxScale]. */
	UFUNCTION(BlueprintCallable, Category = "AR|Placeable")
	void ApplyPinchScale(float ScaleDelta);

	/**
	 * Create an ARPin at the current world transform so ARCore keeps the
	 * object glued to the real world. If the AR session is not yet Running,
	 * schedules a retry until it is.
	 */
	UFUNCTION(BlueprintCallable, Category = "AR|Placeable")
	bool PinToARWorld();

	/** Removes any existing anchor so the object can be moved freely. */
	UFUNCTION(BlueprintCallable, Category = "AR|Placeable")
	void UnpinFromARWorld();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AR|Placeable")
	float MinScale = 0.25f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AR|Placeable")
	float MaxScale = 4.0f;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "AR|Placeable", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<UStaticMeshComponent> Mesh;

private:
	UPROPERTY()
	TObjectPtr<UMaterialInstanceDynamic> HighlightMID;

	UPROPERTY(Transient)
	TObjectPtr<UARPin> AnchorPin;

	FTimerHandle PinRetryHandle;

	bool bIsGrabbed = false;
};
