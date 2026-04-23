// Copyright OreVis. Licensed under MIT.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ARPlaceableActor.generated.h"

class UStaticMeshComponent;
class UMaterialInstanceDynamic;

/**
 * A 3D object the user can place, pinch-select, and drag around the AR world.
 * Spawned by the AR game mode within a fixed radius of the player.
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

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AR|Placeable")
	float MinScale = 0.25f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AR|Placeable")
	float MaxScale = 4.0f;

protected:
	virtual void BeginPlay() override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "AR|Placeable", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<UStaticMeshComponent> Mesh;

private:
	UPROPERTY()
	TObjectPtr<UMaterialInstanceDynamic> HighlightMID;

	bool bIsGrabbed = false;
};
