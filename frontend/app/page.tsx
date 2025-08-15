'use client';

import React, { useState } from 'react';
import { FileText, Upload } from 'lucide-react';
import toast from 'react-hot-toast';
import FileUpload from '@/components/FileUpload';
import ResumeAnalysis from '@/components/ResumeAnalysis';
import Button from '@/components/ui/Button';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { apiService } from '@/lib/api';

export default function Home() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<any>(null);

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setAnalysis(null);
  };

  const handleFileRemove = () => {
    setSelectedFile(null);
    setAnalysis(null);
  };

  const handleAnalyze = async () => {
    if (!selectedFile) {
      toast.error('Please select a resume file first');
      return;
    }

    setIsAnalyzing(true);
    try {
      const result = await apiService.analyzeResume(selectedFile, jobDescription);
      setAnalysis(result);
      toast.success('Resume analyzed successfully!');
    } catch (error) {
      console.error('Analysis error:', error);
      toast.error('Failed to analyze resume. Please try again.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Resume ATS</h1>
          <p className="text-gray-600">Upload your resume for ATS analysis</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Upload Section */}
          <Card>
            <CardHeader>
              <h2 className="text-xl font-semibold">Upload Resume</h2>
            </CardHeader>
            <CardContent className="space-y-4">
              <FileUpload
                onFileSelect={handleFileSelect}
                onFileRemove={handleFileRemove}
                selectedFile={selectedFile}
              />

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Job Description (Optional)
                </label>
                <textarea
                  value={jobDescription}
                  onChange={(e) => setJobDescription(e.target.value)}
                  placeholder="Paste job description for targeted analysis..."
                  className="w-full p-3 border border-gray-300 rounded-lg resize-none"
                  rows={4}
                />
              </div>

              <Button
                onClick={handleAnalyze}
                loading={isAnalyzing}
                disabled={!selectedFile}
                className="w-full"
              >
                {isAnalyzing ? 'Analyzing...' : 'Analyze Resume'}
              </Button>
            </CardContent>
          </Card>

          {/* Results Section */}
          <div>
            {analysis ? (
              <ResumeAnalysis analysis={analysis} />
            ) : (
              <Card>
                <CardContent className="p-8 text-center">
                  <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">Ready to Analyze</h3>
                  <p className="text-gray-600">
                    Upload your resume and click analyze to get started.
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
