// Copyright OreVis. Licensed under MIT.

#include "StartupTachoWidget.h"

#include "Components/Image.h"
#include "Components/ProgressBar.h"
#include "Components/TextBlock.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "TimerManager.h"

void UStartupTachoWidget::NativeConstruct()
{
	Super::NativeConstruct();

	if (UOreVisStartupSubsystem* Subsys = UOreVisStartupSubsystem::Get(this))
	{
		Subsys->OnProgressChanged.AddDynamic(this, &UStartupTachoWidget::HandleProgressChanged);
		// Paint the current value immediately — we may have missed earlier
		// broadcasts if the widget was created after boot.
		ApplyProgress(Subsys->GetProgress01(), Subsys->GetStage());
	}
}

void UStartupTachoWidget::NativeDestruct()
{
	if (UOreVisStartupSubsystem* Subsys = UOreVisStartupSubsystem::Get(this))
	{
		Subsys->OnProgressChanged.RemoveDynamic(this, &UStartupTachoWidget::HandleProgressChanged);
	}
	if (UWorld* World = GetWorld())
	{
		World->GetTimerManager().ClearTimer(HideTimerHandle);
	}
	Super::NativeDestruct();
}

void UStartupTachoWidget::HandleProgressChanged(float Progress01, EOreVisStartupStage Stage)
{
	ApplyProgress(Progress01, Stage);
}

void UStartupTachoWidget::ApplyProgress(float Progress01, EOreVisStartupStage Stage)
{
	if (ProgressBar)
	{
		ProgressBar->SetPercent(Progress01);
	}
	if (PercentLabel)
	{
		PercentLabel->SetText(FText::AsPercent(Progress01));
	}
	if (StageLabel)
	{
		if (UOreVisStartupSubsystem* Subsys = UOreVisStartupSubsystem::Get(this))
		{
			StageLabel->SetText(Subsys->GetStageLabel());
		}
	}
	if (TachoImage)
	{
		// Drive a radial-fill material parameter. Uses the existing material
		// if it's already an MID; otherwise wraps it so we don't mutate the
		// shared asset.
		if (UMaterialInstanceDynamic* MID = TachoImage->GetDynamicMaterial())
		{
			MID->SetScalarParameterValue(TachoProgressParam, Progress01);
		}
	}

	OnTachoProgressUpdated(Progress01, Stage);

	if (bHideWhenReady && Stage == EOreVisStartupStage::Ready)
	{
		if (UWorld* World = GetWorld())
		{
			World->GetTimerManager().SetTimer(HideTimerHandle,
				FTimerDelegate::CreateWeakLambda(this, [this]()
				{
					SetVisibility(ESlateVisibility::Collapsed);
				}),
				FMath::Max(HideDelaySeconds, 0.0f), false);
		}
	}
}
