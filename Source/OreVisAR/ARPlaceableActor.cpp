// Copyright OreVis. Licensed under MIT.

#include "ARPlaceableActor.h"

#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

AARPlaceableActor::AARPlaceableActor()
{
	PrimaryActorTick.bCanEverTick = false;

	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	RootComponent = Mesh;
	Mesh->SetCollisionProfileName(TEXT("BlockAllDynamic"));
	Mesh->SetGenerateOverlapEvents(false);
	Mesh->SetMobility(EComponentMobility::Movable);

	// Default to the engine's cube so the class is usable without Blueprint
	// subclassing. Designers can override via a BP child.
	static ConstructorHelpers::FObjectFinder<UStaticMesh> CubeMesh(
		TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (CubeMesh.Succeeded())
	{
		Mesh->SetStaticMesh(CubeMesh.Object);
		Mesh->SetRelativeScale3D(FVector(0.25f));
	}

	Tags.Add(FName(TEXT("ARPlaceable")));
}

void AARPlaceableActor::BeginPlay()
{
	Super::BeginPlay();

	if (Mesh && Mesh->GetMaterial(0))
	{
		HighlightMID = Mesh->CreateAndSetMaterialInstanceDynamic(0);
	}
}

void AARPlaceableActor::SetGrabbed(bool bGrabbed)
{
	if (bIsGrabbed == bGrabbed)
	{
		return;
	}
	bIsGrabbed = bGrabbed;

	if (HighlightMID)
	{
		// Tint the object while grabbed so the user gets clear feedback
		// through the glasses.
		const FLinearColor Tint = bGrabbed ? FLinearColor(1.2f, 0.8f, 0.2f)
		                                   : FLinearColor::White;
		HighlightMID->SetVectorParameterValue(TEXT("Tint"), Tint);
	}
}

void AARPlaceableActor::ApplyPinchScale(float ScaleDelta)
{
	if (FMath::IsNearlyZero(ScaleDelta))
	{
		return;
	}
	const FVector Current = GetActorScale3D();
	const float NewUniform = FMath::Clamp(Current.X * ScaleDelta, MinScale, MaxScale);
	SetActorScale3D(FVector(NewUniform));
}
