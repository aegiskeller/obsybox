using System.ComponentModel.Composition;

namespace TestPlugin
{
    [Export]
    public class SimpleTestPlugin
    {
        public string Name => "Test Plugin";
    }
}