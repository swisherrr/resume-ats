'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, FileText, Target, TrendingUp, BookOpen } from 'lucide-react';
import Link from 'next/link';
import toast from 'react-hot-toast';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import { apiService } from '@/lib/api';

export default function JobMatchPage() {
  const [resumeText, setResumeText] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [matchResult, setMatchResult] = useState<any>(null);

  const handleAnalyze = async () => {
    if (!resumeText.trim() || !jobDescription.trim()) {
      toast.error('Please provide both resume text and job description');
      return;
    }

    setIsAnalyzing(true);
    try {
      const result = await apiService.matchResumeToJob(resumeText, jobDescription);
      setMatchResult(result);
      toast.success('Job matching analysis completed!');
    } catch (error) {
      console.error('Matching error:', error);
      toast.error('Failed to analyze job match. Please try again.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getMatchColor = (percentage: number) => {
    if (percentage >= 80) return 'text-success-600';
    if (percentage >= 60) return 'text-warning-600';
    return 'text-error-600';
  };

  const getMatchBadge = (percentage: number) => {
    if (percentage >= 80) return 'bg-success-100 text-success-800';
    if (percentage >= 60) return 'bg-warning-100 text-warning-800';
    return 'bg-error-100 text-error-800';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center py-6">
            <Link href="/" className="mr-6">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
            </Link>
            <div className="flex items-center space-x-3">
              <div className="bg-primary-600 p-2 rounded-lg">
                <Target className="h-8 w-8 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Job Matching</h1>
                <p className="text-sm text-gray-600">Compare your resume with job descriptions</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Input Section */}
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <h3 className="text-xl font-semibold text-gray-900">Resume Text</h3>
                <p className="text-gray-600">Paste your resume content here</p>
              </CardHeader>
              <CardContent>
                <textarea
                  value={resumeText}
                  onChange={(e) => setResumeText(e.target.value)}
                  placeholder="Paste your resume text here... (You can copy from your resume document)"
                  className="input-field h-64 resize-none"
                  rows={12}
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <h3 className="text-xl font-semibold text-gray-900">Job Description</h3>
                <p className="text-gray-600">Paste the job description you want to match against</p>
              </CardHeader>
              <CardContent>
                <textarea
                  value={jobDescription}
                  onChange={(e) => setJobDescription(e.target.value)}
                  placeholder="Paste the job description here..."
                  className="input-field h-64 resize-none"
                  rows={12}
                />
              </CardContent>
            </Card>

            <Button
              onClick={handleAnalyze}
              loading={isAnalyzing}
              disabled={!resumeText.trim() || !jobDescription.trim()}
              className="w-full"
              size="lg"
            >
              {isAnalyzing ? 'Analyzing Match...' : 'Analyze Job Match'}
            </Button>
          </div>

          {/* Results Section */}
          <div className="lg:col-span-1">
            {matchResult ? (
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                className="space-y-6"
              >
                {/* Match Score */}
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <h3 className="text-lg font-semibold text-gray-900">Match Score</h3>
                      <div className={`px-3 py-1 rounded-full text-sm font-medium ${getMatchBadge(matchResult.match_percentage)}`}>
                        {matchResult.match_percentage}%
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="text-center">
                      <div className={cn('text-4xl font-bold mb-2', getMatchColor(matchResult.match_percentage))}>
                        {matchResult.match_percentage}%
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-3 mb-4">
                        <div
                          className={cn('h-3 rounded-full transition-all duration-500', {
                            'bg-success-500': matchResult.match_percentage >= 80,
                            'bg-warning-500': matchResult.match_percentage >= 60 && matchResult.match_percentage < 80,
                            'bg-error-500': matchResult.match_percentage < 60,
                          })}
                          style={{ width: `${matchResult.match_percentage}%` }}
                        />
                      </div>
                      <p className="text-sm text-gray-600">
                        {matchResult.match_percentage >= 80
                          ? 'Excellent match! Your resume aligns well with this job.'
                          : matchResult.match_percentage >= 60
                          ? 'Good match, but there\'s room for improvement.'
                          : 'Low match. Consider tailoring your resume for this position.'}
                      </p>
                    </div>
                  </CardContent>
                </Card>

                {/* Pass Probability */}
                <Card>
                  <CardHeader>
                    <div className="flex items-center space-x-2">
                      <TrendingUp className="h-5 w-5 text-primary-600" />
                      <h3 className="text-lg font-semibold text-gray-900">Pass Probability</h3>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="text-center">
                      <div className="text-3xl font-bold text-primary-600 mb-2">
                        {matchResult.pass_probability}%
                      </div>
                      <p className="text-sm text-gray-600">
                        Estimated probability of passing the initial ATS screening
                      </p>
                    </div>
                  </CardContent>
                </Card>

                {/* Skill Gaps */}
                <Card>
                  <CardHeader>
                    <div className="flex items-center space-x-2">
                      <Target className="h-5 w-5 text-error-600" />
                      <h3 className="text-lg font-semibold text-gray-900">Skill Gaps</h3>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {matchResult.gaps.length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                          {matchResult.gaps.map((gap: string, index: number) => (
                            <span
                              key={index}
                              className="px-3 py-1 bg-error-100 text-error-800 text-sm rounded-full"
                            >
                              {gap}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <p className="text-success-600 text-sm">No significant skill gaps detected!</p>
                      )}
                    </div>
                  </CardContent>
                </Card>

                {/* Learning Resources */}
                {matchResult.learning_resources && matchResult.learning_resources.length > 0 && (
                  <Card>
                    <CardHeader>
                      <div className="flex items-center space-x-2">
                        <BookOpen className="h-5 w-5 text-primary-600" />
                        <h3 className="text-lg font-semibold text-gray-900">Learning Resources</h3>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <ul className="space-y-2">
                        {matchResult.learning_resources.map((resource: string, index: number) => (
                          <li key={index} className="text-sm text-gray-700">
                            • {resource}
                          </li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                )}
              </motion.div>
            ) : (
              <Card>
                <CardContent className="p-8 text-center">
                  <Target className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">Ready to Match</h3>
                  <p className="text-gray-600">
                    Enter your resume text and job description to see how well they match.
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function cn(...classes: string[]) {
  return classes.filter(Boolean).join(' ');
}
