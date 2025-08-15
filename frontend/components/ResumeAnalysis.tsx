import React from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { TrendingUp, Target, FileText, CheckCircle, AlertCircle } from 'lucide-react';

interface ResumeAnalysisProps {
  analysis: {
    ats_score: number;
    keywords: string[];
    skills: string[];
    suggestions: string[];
    matched_keywords: string[];
    missing_keywords: string[];
    extracted_text: string;
  };
}

const ResumeAnalysis: React.FC<ResumeAnalysisProps> = ({ analysis }) => {
  return (
    <Card>
      <CardHeader>
        <h2 className="text-xl font-semibold">Analysis Results</h2>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* ATS Score */}
        <div className="text-center p-4 bg-gray-50 rounded-lg">
          <div className="text-3xl font-bold text-blue-600 mb-2">
            {analysis.ats_score}%
          </div>
          <div className="text-sm text-gray-600">ATS Compatibility Score</div>
        </div>

        {/* Keywords */}
        <div>
          <h3 className="font-semibold mb-3 flex items-center">
            <Target className="h-4 w-4 mr-2" />
            Keywords Found
          </h3>
          <div className="flex flex-wrap gap-2">
            {analysis.keywords.slice(0, 10).map((keyword, index) => (
              <span
                key={index}
                className="px-2 py-1 bg-green-100 text-green-800 text-sm rounded"
              >
                {keyword}
              </span>
            ))}
          </div>
        </div>

        {/* Skills */}
        <div>
          <h3 className="font-semibold mb-3 flex items-center">
            <CheckCircle className="h-4 w-4 mr-2" />
            Skills Identified
          </h3>
          <div className="flex flex-wrap gap-2">
            {analysis.skills.slice(0, 8).map((skill, index) => (
              <span
                key={index}
                className="px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded"
              >
                {skill}
              </span>
            ))}
          </div>
        </div>

        {/* Suggestions */}
        {analysis.suggestions.length > 0 && (
          <div>
            <h3 className="font-semibold mb-3 flex items-center">
              <AlertCircle className="h-4 w-4 mr-2" />
              Suggestions
            </h3>
            <ul className="space-y-2">
              {analysis.suggestions.slice(0, 5).map((suggestion, index) => (
                <li key={index} className="text-sm text-gray-700 flex items-start">
                  <span className="text-blue-500 mr-2">•</span>
                  {suggestion}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Missing Keywords */}
        {analysis.missing_keywords.length > 0 && (
          <div>
            <h3 className="font-semibold mb-3 text-orange-600 flex items-center">
              <AlertCircle className="h-4 w-4 mr-2" />
              Missing Keywords
            </h3>
            <div className="flex flex-wrap gap-2">
              {analysis.missing_keywords.slice(0, 6).map((keyword, index) => (
                <span
                  key={index}
                  className="px-2 py-1 bg-orange-100 text-orange-800 text-sm rounded"
                >
                  {keyword}
                </span>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default ResumeAnalysis;
