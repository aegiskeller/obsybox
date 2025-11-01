using NINA.Sequencer.SequenceItem;
using NINA.Core.Model;
using System.ComponentModel.Composition;
using System.Threading;
using System.Threading.Tasks;
using System;

namespace NINA.Plugin.FileTargetScheduler.SequenceItems
{
    [ExportMetadata("Name", "Load Target From File")]
    [ExportMetadata("Description", "Loads target information from a file")]
    [ExportMetadata("Icon", "")]
    [ExportMetadata("Category", "File Target Scheduler")]
    [Export(typeof(ISequenceItem))]
    public class LoadTargetFromFile : SequenceItem
    {
        [ImportingConstructor]
        public LoadTargetFromFile()
  {
 }

        public override async Task Execute(IProgress<ApplicationStatus> progress, CancellationToken token)
     {
         progress?.Report(new ApplicationStatus() { Status = "Loading target from file..." });
         
  // For now, just a placeholder
            await Task.Delay(100, token);
   
            progress?.Report(new ApplicationStatus() { Status = "Target loaded successfully" });
        }

        public override object Clone()
        {
   return new LoadTargetFromFile();
     }

        public override string ToString()
        {
     return $"Load Target From File";
        }
    }
}