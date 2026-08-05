import {
  CheckCircleIcon,
  Cog6ToothIcon,
  LanguageIcon,
  ShieldCheckIcon,
} from "@heroicons/react/24/outline";

const capabilities = [
  {
    title: "Automatic language detection",
    description:
      "Faster-Whisper detects the spoken language unless WHISPER_LANGUAGE is explicitly configured.",
    icon: LanguageIcon,
  },
  {
    title: "Multilingual transcription",
    description:
      "Use a multilingual Faster-Whisper model such as small, medium, or large-v3. English-only models are not used by default.",
    icon: CheckCircleIcon,
  },
  {
    title: "Private processing",
    description:
      "Transcription runs inside the worker. Structured insights stay local unless an operator explicitly selects an external AI provider.",
    icon: ShieldCheckIcon,
  },
];

const configuration = [
  ["FW_MODEL", "small", "Multilingual transcription model"],
  ["WHISPER_LANGUAGE", "", "Optional ISO language code; blank enables detection"],
  ["AI_PROVIDER", "local", "Local insight extraction by default"],
  ["LOCAL_LLM_BASE_URL", "", "Optional OpenAI-compatible local model endpoint"],
];

export default function LanguageSamplesPage() {
  return (
    <div className="space-y-8">
      <header className="max-w-3xl">
        <div className="mb-3 inline-flex items-center rounded-full bg-blue-50 px-3 py-1 text-sm font-medium text-blue-700">
          <LanguageIcon className="mr-2 h-4 w-4" />
          Multilingual configuration
        </div>
        <h1 className="text-3xl font-bold text-gray-900">Language support</h1>
        <p className="mt-3 text-gray-600">
          This page documents the real transcription configuration. It does not
          display generated sample results or simulated processing times.
        </p>
      </header>

      <section className="grid gap-5 md:grid-cols-3">
        {capabilities.map(({ title, description, icon: Icon }) => (
          <article
            key={title}
            className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm"
          >
            <Icon className="mb-4 h-7 w-7 text-blue-600" />
            <h2 className="font-semibold text-gray-900">{title}</h2>
            <p className="mt-2 text-sm leading-6 text-gray-600">{description}</p>
          </article>
        ))}
      </section>

      <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="mb-5 flex items-center">
          <Cog6ToothIcon className="mr-2 h-6 w-6 text-gray-600" />
          <h2 className="text-xl font-semibold text-gray-900">
            Recommended environment settings
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-left text-sm">
            <thead>
              <tr className="text-gray-500">
                <th className="px-3 py-3 font-medium">Variable</th>
                <th className="px-3 py-3 font-medium">Default</th>
                <th className="px-3 py-3 font-medium">Purpose</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {configuration.map(([variable, value, purpose]) => (
                <tr key={variable}>
                  <td className="px-3 py-3 font-mono text-gray-900">{variable}</td>
                  <td className="px-3 py-3 font-mono text-gray-700">
                    {value || "blank"}
                  </td>
                  <td className="px-3 py-3 text-gray-600">{purpose}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-xl border border-amber-200 bg-amber-50 p-6">
        <h2 className="font-semibold text-amber-950">Current limitation</h2>
        <p className="mt-2 text-sm leading-6 text-amber-900">
          Transcription support is multilingual, but extraction quality still
          depends on the configured insight provider. Language-specific
          evaluation datasets and reproducible accuracy benchmarks remain part
          of the product roadmap.
        </p>
      </section>
    </div>
  );
}
