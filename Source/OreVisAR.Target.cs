// Copyright OreVis. Licensed under MIT.

using UnrealBuildTool;
using System.Collections.Generic;

public class OreVisARTarget : TargetRules
{
	public OreVisARTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.V5;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("OreVisAR");
	}
}
