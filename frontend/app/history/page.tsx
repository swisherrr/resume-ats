'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, FileText, Calendar, TrendingUp } from 'lucide-react';
import Link from 'next/link';
import toast from 'react-hot-toast';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import { apiService } from '@/lib/api';
import { formatDate } from '@/lib/utils';

interface ResumeHistory {
  _id: string;
  filename: string;
  created_at: string;
  analysis_results: {
    ats_score: number;
    keywords: string[];
    skills: string[];
  };
}

export default function HistoryPage() {
  const [history, setHistory] = useState<ResumeHistory[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const response = await apiService.getResumeHistory();
      setHistory(response.resumes || []);
    } catch (error) {
      console.error('Failed to load history:', error);
      toast.error('Failed to load analysis history');
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-success-600';
    if (score >= 60) return 'text-warning-600';
    return 'text-error-600';
  };

  const getScoreBadge = (score: number) => {
    if (score >= 80) return 'bg-success-100 text-success-800';
    if (score >= 60) return 'bg-warning-100 text-warning-800';
    return 'bg-error-100 text-error-800';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading analysis history...</p>
        </div>
      </div>
    );
  }

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
                <FileText className="h-8 w-8 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Analysis History</h1>
                <p className="text-sm text-gray-600">View your previous resume analyses</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {history.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-12"
          >
            <FileText className="h-16 w-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-xl font-medium text-gray-900 mb-2">No Analysis History</h3>
            <p className="text-gray-600 mb-6">
              You haven't analyzed any resumes yet. Start by uploading your first resume.
            </p>
            <Link href="/">
              <Button size="lg">
                Upload Resume
              </Button>
            </Link>
          </motion.div>
        ) : (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold text-gray-900">
                Recent Analyses ({history.length})
              </h2>
              <Button onClick={loadHistory} variant="outline">
                Refresh
              </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {history.map((resume, index) => (
                <motion.div
                  key={resume._id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                >
                  <Card className="h-full hover:shadow-md transition-shadow duration-200">
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h3 className="font-semibold text-gray-900 truncate">
                            {resume.filename}
                          </h3>
                          <div className="flex items-center space-x-2 mt-2">
                            <Calendar className="h-4 w-4 text-gray-400" />
                            <span className="text-sm text-gray-600">
                              {formatDate(resume.created_at)}
                            </span>
                          </div>
                        </div>
                        <div className={`px-2 py-1 rounded-full text-xs font-medium ${getScoreBadge(resume.analysis_results.ats_score)}`}>
                          {resume.analysis_results.ats_score}%
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        <div className="flex items-center space-x-2">
                          <TrendingUp className="h-4 w-4 text-primary-600" />
                          <span className={`text-sm font-medium ${getScoreColor(resume.analysis_results.ats_score)}`}>
                            ATS Score: {resume.analysis_results.ats_score}%
                          </span>
                        </div>
                        
                        <div>
                          <p className="text-xs font-medium text-gray-700 mb-1">Skills Detected:</p>
                          <div className="flex flex-wrap gap-1">
                            {resume.analysis_results.skills.slice(0, 3).map((skill, skillIndex) => (
                              <span
                                key={skillIndex}
                                className="px-2 py-1 bg-primary-100 text-primary-800 text-xs rounded-full"
                              >
                                {skill}
                              </span>
                            ))}
                            {resume.analysis_results.skills.length > 3 && (
                              <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-full">
                                +{resume.analysis_results.skills.length - 3} more
                              </span>
                            )}
                          </div>
                        </div>

                        <div>
                          <p className="text-xs font-medium text-gray-700 mb-1">Keywords Found:</p>
                          <div className="flex flex-wrap gap-1">
                            {resume.analysis_results.keywords.slice(0, 3).map((keyword, keywordIndex) => (
                              <span
                                key={keywordIndex}
                                className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-full"
                              >
                                {keyword}
                              </span>
                            ))}
                            {resume.analysis_results.keywords.length > 3 && (
                              <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-full">
                                +{resume.analysis_results.keywords.length - 3} more
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
