// Copyright OreVis. Licensed under MIT.

using UnrealBuildTool;

public class OreVisAR : ModuleRules
{
	public OreVisAR(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core",
			"CoreUObject",
			"Engine",
			"InputCore",
			"EnhancedInput",
			"AugmentedReality",
			"ARUtilities",
			"HeadMountedDisplay",
			"XRBase",
			"UMG"                     // widget classes ship in this module's public API
		});

		PrivateDependencyModuleNames.AddRange(new string[]
		{
			"Slate",
			"SlateCore",
			"RenderCore",
			"RHI"
		});

		// ARCore is only shipped on Android.
		if (Target.Platform == UnrealTargetPlatform.Android)
		{
			PrivateDependencyModuleNames.Add("GoogleARCoreBase");
		}
	}
}
