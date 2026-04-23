// Copyright OreVis. Licensed under MIT.

#include "OreVisStartupSubsystem.h"

#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "OreVisAR.h"

void UOreVisStartupSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	// As soon as the subsystem is alive, the module has loaded — nudge the
	// tacho off zero so the user sees feedback the instant the HUD appears.
	SetStage(EOreVisStartupStage::LoadingAssets);
}

void UOreVisStartupSubsystem::SetStage(EOreVisStartupStage NewStage)
{
	// Skip backwards transitions so a late-firing stage doesn't wipe out
	// progress already reported by a faster system.
	if (CurrentStage != EOreVisStartupStage::Failed &&
		static_cast<uint8>(NewStage) < static_cast<uint8>(CurrentStage))
	{
		return;
	}
	if (NewStage == CurrentStage)
	{
		return;
	}
	CurrentStage = NewStage;
	CachedProgress = ProgressForStage(NewStage);
	BroadcastCurrent();
}

void UOreVisStartupSubsystem::ForceStage(EOreVisStartupStage NewStage)
{
	CurrentStage = NewStage;
	CachedProgress = ProgressForStage(NewStage);
	BroadcastCurrent();
}

FText UOreVisStartupSubsystem::GetStageLabel() const
{
	const UEnum* EnumPtr = StaticEnum<EOreVisStartupStage>();
	if (!EnumPtr)
	{
		return FText::GetEmpty();
	}
	return EnumPtr->GetDisplayNameTextByValue(static_cast<int64>(CurrentStage));
}

UOreVisStartupSubsystem* UOreVisStartupSubsystem::Get(const UObject* WorldContext)
{
	if (!WorldContext)
	{
		return nullptr;
	}
	if (const UWorld* World = WorldContext->GetWorld())
	{
		if (UGameInstance* GI = World->GetGameInstance())
		{
			return GI->GetSubsystem<UOreVisStartupSubsystem>();
		}
	}
	return nullptr;
}

float UOreVisStartupSubsystem::ProgressForStage(EOreVisStartupStage Stage)
{
	switch (Stage)
	{
	case EOreVisStartupStage::NotStarted:         return 0.00f;
	case EOreVisStartupStage::LoadingAssets:      return 0.10f;
	case EOreVisStartupStage::StartingARSession:  return 0.25f;
	case EOreVisStartupStage::WaitingForTracking: return 0.50f;
	case EOreVisStartupStage::ScatteringObjects:  return 0.75f;
	case EOreVisStartupStage::Ready:              return 1.00f;
	case EOreVisStartupStage::Failed:             return 0.00f;
	}
	return 0.0f;
}

void UOreVisStartupSubsystem::BroadcastCurrent()
{
	UE_LOG(LogOreVisAR, Log, TEXT("Startup stage → %s (%.0f%%)"),
		*GetStageLabel().ToString(), CachedProgress * 100.f);
	OnProgressChanged.Broadcast(CachedProgress, CurrentStage);
}
