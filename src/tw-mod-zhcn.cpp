// tw-mod-zhcn: Simplified Chinese localisation for Tortoise-WoW.
// The module ships data only (data/sql/world); this script just reports that it is loaded.
#include "ScriptObjects.h"
#include "Log.h"

namespace
{
    class TwModZhcnWorldScript : public WorldScript
    {
    public:
        TwModZhcnWorldScript()
            : WorldScript("tw-mod-zhcn_world", { WORLDHOOK_ON_STARTUP })
        {
        }

        void OnStartup() override
        {
            sLog.outString("[tw-mod-zhcn] module loaded.");
        }
    };
}

void Addtw_mod_zhcnScripts()
{
    new TwModZhcnWorldScript();
}
