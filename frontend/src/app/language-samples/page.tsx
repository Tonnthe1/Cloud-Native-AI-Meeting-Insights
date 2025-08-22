'use client';

import { useState } from 'react';
import Layout from '@/components/Layout';

interface SampleResult {
  language: string;
  duration: number;
  keywords: string[];
  summary: string;
  status: 'idle' | 'processing' | 'completed' | 'error';
  meetingId?: number;
  jobId?: string;
  error?: string;
}

interface LanguageSample {
  id: string;
  name: string;
  language: string;
  description: string;
  sampleText: string;
}

const languageSamples: LanguageSample[] = [
  {
    id: 'english',
    name: 'English Business Meeting',
    language: 'English',
    description: 'Quarterly review discussion',
    sampleText: 'Good morning everyone. Today we\'ll be reviewing our Q3 performance metrics and discussing action items for Q4. Let\'s start with the sales numbers...'
  },
  {
    id: 'chinese',
    name: 'Chinese Team Meeting',
    language: 'Chinese (Mandarin)',
    description: 'Product development update',
    sampleText: '大家好，今天我们讨论新产品的开发进展。首先，让我们看看技术团队的更新...'
  },
  {
    id: 'spanish',
    name: 'Spanish Project Review',
    language: 'Spanish',
    description: 'Weekly project status meeting',
    sampleText: 'Buenos días equipo. Hoy revisaremos el progreso del proyecto y los próximos pasos. Comenzamos con el informe de desarrollo...'
  },
  {
    id: 'french',
    name: 'French Strategy Session',
    language: 'French',
    description: 'Marketing strategy discussion',
    sampleText: 'Bonjour à tous. Aujourd\'hui nous allons discuter de notre stratégie marketing pour le prochain trimestre. Commençons par l\'analyse du marché...'
  },
  {
    id: 'japanese',
    name: 'Japanese Planning Meeting',
    language: 'Japanese',
    description: 'Product roadmap planning',
    sampleText: 'みなさん、こんにちは。今日は来年度の製品ロードマップについて話し合います。まず、市場調査の結果から始めましょう...'
  }
];

export default function LanguageSamples() {
  const [results, setResults] = useState<Record<string, SampleResult>>({});
  const [isProcessingAll, setIsProcessingAll] = useState(false);

  // Mock processing function that simulates the transcription pipeline
  const processSample = async (sample: LanguageSample): Promise<SampleResult> => {
    // Simulate processing time
    await new Promise(resolve => setTimeout(resolve, 2000 + Math.random() * 3000));
    
    // Mock results based on the sample
    const mockResults: Record<string, Partial<SampleResult>> = {
      english: {
        keywords: ['Q3', 'performance', 'metrics', 'sales', 'quarterly', 'review', 'action items', 'Q4'],
        summary: '• Review of Q3 performance metrics\n• Discussion of sales numbers\n• Planning action items for Q4\n• Focus on quarterly objectives'
      },
      chinese: {
        keywords: ['产品开发', '技术团队', '新产品', '进展', '更新', '讨论'],
        summary: '• 新产品开发进展更新\n• 技术团队报告\n• 开发里程碑回顾\n• 下一阶段计划'
      },
      spanish: {
        keywords: ['proyecto', 'progreso', 'desarrollo', 'equipo', 'informe', 'pasos'],
        summary: '• Revisión del progreso del proyecto\n• Informe del equipo de desarrollo\n• Próximos pasos identificados\n• Estado semanal actualizado'
      },
      french: {
        keywords: ['stratégie', 'marketing', 'trimestre', 'marché', 'analyse', 'discussion'],
        summary: '• Discussion de stratégie marketing\n• Analyse du marché trimestre\n• Planification des campagnes\n• Objectifs marketing définis'
      },
      japanese: {
        keywords: ['製品', 'ロードマップ', '来年度', '市場調査', '計画', '開発'],
        summary: '• 来年度製品ロードマップ計画\n• 市場調査結果の検討\n• 開発優先順位の決定\n• リリース予定の調整'
      }
    };

    const mockData = mockResults[sample.id] || {};
    
    return {
      language: sample.language,
      duration: 45 + Math.random() * 120, // 45-165 seconds
      keywords: mockData.keywords || ['meeting', 'discussion', 'team'],
      summary: mockData.summary || '• General meeting discussion\n• Team updates shared\n• Action items identified',
      status: 'completed',
      meetingId: Math.floor(Math.random() * 1000) + 1,
      jobId: `mock_job_${Date.now()}_${sample.id}`
    };
  };

  const handleProcessSample = async (sample: LanguageSample) => {
    setResults(prev => ({
      ...prev,
      [sample.id]: {
        language: sample.language,
        duration: 0,
        keywords: [],
        summary: '',
        status: 'processing'
      }
    }));

    try {
      const result = await processSample(sample);
      setResults(prev => ({
        ...prev,
        [sample.id]: result
      }));
    } catch (error) {
      setResults(prev => ({
        ...prev,
        [sample.id]: {
          language: sample.language,
          duration: 0,
          keywords: [],
          summary: '',
          status: 'error',
          error: error instanceof Error ? error.message : 'Processing failed'
        }
      }));
    }
  };

  const handleProcessAll = async () => {
    setIsProcessingAll(true);
    
    // Reset all results
    const initialResults: Record<string, SampleResult> = {};
    languageSamples.forEach(sample => {
      initialResults[sample.id] = {
        language: sample.language,
        duration: 0,
        keywords: [],
        summary: '',
        status: 'processing'
      };
    });
    setResults(initialResults);

    // Process all samples concurrently
    try {
      const promises = languageSamples.map(async (sample) => {
        try {
          const result = await processSample(sample);
          setResults(prev => ({
            ...prev,
            [sample.id]: result
          }));
        } catch (error) {
          setResults(prev => ({
            ...prev,
            [sample.id]: {
              language: sample.language,
              duration: 0,
              keywords: [],
              summary: '',
              status: 'error',
              error: error instanceof Error ? error.message : 'Processing failed'
            }
          }));
        }
      });

      await Promise.all(promises);
    } finally {
      setIsProcessingAll(false);
    }
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <Layout>
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            Language Samples Demo
          </h1>
          <p className="text-gray-600 mb-6">
            Test our AI meeting insights pipeline with sample audio in 5 different languages. 
            Each sample demonstrates automatic transcription, language detection, keyword extraction, and summary generation.
          </p>
          
          <button
            onClick={handleProcessAll}
            disabled={isProcessingAll}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {isProcessingAll ? 'Processing All Samples...' : 'Run All Samples Through Pipeline'}
          </button>
        </div>

        <div className="grid gap-6 md:grid-cols-1 lg:grid-cols-2">
          {languageSamples.map((sample) => {
            const result = results[sample.id];
            
            return (
              <div key={sample.id} className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-1">
                      {sample.name}
                    </h3>
                    <p className="text-sm text-gray-500">
                      {sample.language} • {sample.description}
                    </p>
                  </div>
                  
                  <button
                    onClick={() => handleProcessSample(sample)}
                    disabled={result?.status === 'processing' || isProcessingAll}
                    className="bg-gray-100 text-gray-700 px-4 py-2 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
                  >
                    {result?.status === 'processing' ? 'Processing...' : 'Process'}
                  </button>
                </div>

                <div className="mb-4 p-3 bg-gray-50 rounded text-sm text-gray-600 italic">
                  "{sample.sampleText}"
                </div>

                {result && (
                  <div className="space-y-3">
                    {result.status === 'processing' && (
                      <div className="flex items-center space-x-2">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                        <span className="text-sm text-gray-600">Processing audio...</span>
                      </div>
                    )}

                    {result.status === 'completed' && (
                      <>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <span className="font-medium text-gray-700">Detected Language:</span>
                            <div className="text-gray-900">{result.language}</div>
                          </div>
                          <div>
                            <span className="font-medium text-gray-700">Duration:</span>
                            <div className="text-gray-900">{formatDuration(result.duration)}</div>
                          </div>
                        </div>

                        <div>
                          <span className="font-medium text-gray-700 block mb-2">Keywords:</span>
                          <div className="flex flex-wrap gap-2">
                            {result.keywords.map((keyword, idx) => (
                              <span
                                key={idx}
                                className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs"
                              >
                                {keyword}
                              </span>
                            ))}
                          </div>
                        </div>

                        <div>
                          <span className="font-medium text-gray-700 block mb-2">Summary:</span>
                          <div className="text-gray-900 text-sm whitespace-pre-line">
                            {result.summary}
                          </div>
                        </div>

                        {result.meetingId && (
                          <div className="text-xs text-gray-500">
                            Meeting ID: {result.meetingId} | Job ID: {result.jobId}
                          </div>
                        )}
                      </>
                    )}

                    {result.status === 'error' && (
                      <div className="text-red-600 text-sm">
                        Error: {result.error || 'Processing failed'}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div className="mt-8 p-6 bg-blue-50 rounded-lg">
          <h3 className="text-lg font-semibold text-blue-900 mb-2">
            About This Demo
          </h3>
          <p className="text-blue-800 text-sm">
            This demonstration showcases our cloud-native AI meeting insights platform's ability to:
          </p>
          <ul className="list-disc list-inside text-blue-800 text-sm mt-2 space-y-1">
            <li>Automatically detect and transcribe speech in multiple languages</li>
            <li>Extract relevant keywords and key topics from meeting content</li>
            <li>Generate intelligent summaries with action items and decisions</li>
            <li>Process audio asynchronously using a distributed worker architecture</li>
            <li>Scale horizontally with Redis queuing and PostgreSQL storage</li>
          </ul>
        </div>
      </div>
    </Layout>
  );
}