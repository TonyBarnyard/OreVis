// Copyright OreVis. Licensed under MIT.

#include "ARSpawnButtonWidget.h"

#include "ARPlaceableActor.h"
#include "Components/Button.h"
#include "OreVisAR.h"
#include "OreVisARPawn.h"

void UARSpawnButtonWidget::NativeConstruct()
{
	Super::NativeConstruct();
	if (SpawnButton)
	{
		SpawnButton->OnClicked.AddDynamic(this, &UARSpawnButtonWidget::HandleSpawnClicked);
	}
	else
	{
		UE_LOG(LogOreVisAR, Warning,
			TEXT("UARSpawnButtonWidget: BP has no `SpawnButton` — tap-to-spawn disabled."));
	}
}

void UARSpawnButtonWidget::NativeDestruct()
{
	if (SpawnButton)
	{
		SpawnButton->OnClicked.RemoveDynamic(this, &UARSpawnButtonWidget::HandleSpawnClicked);
	}
	Super::NativeDestruct();
}

void UARSpawnButtonWidget::HandleSpawnClicked()
{
	AOreVisARPawn* Pawn = Cast<AOreVisARPawn>(GetOwningPlayerPawn());
	if (!Pawn)
	{
		UE_LOG(LogOreVisAR, Warning, TEXT("Spawn click: no OreVisARPawn available."));
		return;
	}
	Pawn->SpawnPlaceableInFront(SpawnDistanceCm, SpawnClassOverride);
}
