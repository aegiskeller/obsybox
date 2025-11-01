using NINA.Plugin;
using NINA.Plugin.Interfaces;
using System.Collections.Generic;
using System.ComponentModel.Composition;
using System.Threading.Tasks;

namespace NINA.Plugin.FileTargetScheduler
{
    [Export(typeof(IPluginManifest))]
    public class FileTargetSchedulerPlugin : PluginBase
   {
        [ImportingConstructor]
  public FileTargetSchedulerPlugin()
        {
      }

        public new string Name => "File Target Scheduler";

    public new string ContentId => this.GetType().FullName;

     public new IList<string> SupportedVersions => new List<string> { "3.0", "3.1" };

       public new string Version => "1.0.0.0";
        
        public new string Author => "obsybox @aegiskeller";

        public new Task Initialize()
     {
      return Task.CompletedTask;
        }

   public new Task Teardown()
    {
   return Task.CompletedTask;
   }
 }
}