// Copyright OreVis. Licensed under MIT.

using UnrealBuildTool;
using System.Collections.Generic;

public class OreVisAREditorTarget : TargetRules
{
	public OreVisAREditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.V5;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("OreVisAR");
	}
}
