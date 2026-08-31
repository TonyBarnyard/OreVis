// Copyright OreVis. Licensed under MIT.

#include "OreVisAR.h"

DEFINE_LOG_CATEGORY(LogOreVisAR);

void FOreVisARModule::StartupModule()
{
	UE_LOG(LogOreVisAR, Log, TEXT("OreVisAR module started."));
}

void FOreVisARModule::ShutdownModule()
{
	UE_LOG(LogOreVisAR, Log, TEXT("OreVisAR module shut down."));
}

IMPLEMENT_PRIMARY_GAME_MODULE(FOreVisARModule, OreVisAR, "OreVisAR");
