using Newtonsoft.Json;

namespace NINA.Plugin.FileTargetScheduler.Models
{
    public class TargetInfo
    {
        [JsonProperty("targetName")]
        public string TargetName { get; set; }

        [JsonProperty("raHours")]
        public int RAHours { get; set; }

        [JsonProperty("raMinutes")]
        public int RAMinutes { get; set; }

        [JsonProperty("raSeconds")]
        public double RASeconds { get; set; }

        [JsonProperty("negativeDec")]
        public bool NegativeDec { get; set; }

        [JsonProperty("decDegrees")]
        public int DecDegrees { get; set; }

        [JsonProperty("decMinutes")]
        public int DecMinutes { get; set; }

        [JsonProperty("decSeconds")]
        public double DecSeconds { get; set; }

        [JsonProperty("exposureTime")]
        public double ExposureTime { get; set; } = 40;

        [JsonProperty("iterations")]
        public int Iterations { get; set; } = 10;

        [JsonProperty("filter")]
        public string Filter { get; set; } = "V";

        [JsonProperty("priority")]
        public int Priority { get; set; } = 1;
    }
}