'use client';

import React, { useEffect, useState } from 'react';
import { Document, Page } from 'react-pdf';
import axios from 'axios';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import { useUser } from '@clerk/nextjs';
import Navigation from '../../../components/Navigation';

interface Violation {
  text: string;
  rule: string;
  explanation: string;
  suggestion: string;
}

interface ComplianceResult {
  document_id: string;
  status: string;
  violations: Violation[];
  timestamp: string;
}

export default function ResultsPage({ params }: { params: { id: string } }) {
  const { user, isLoaded: isUserLoaded } = useUser();
  const [result, setResult] = useState<ComplianceResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState(1);

  useEffect(() => {
    const fetchResults = async () => {
      if (!user) return;

      try {
        const token = await user.getToken();
        const response = await axios.get(
          `${process.env.NEXT_PUBLIC_API_URL}/results/${params.id}`,
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        );
        setResult(response.data);
      } catch (err) {
        setError('Failed to fetch results. Please try again.');
        console.error('Fetch error:', err);
      } finally {
        setLoading(false);
      }
    };

    if (isUserLoaded) {
      fetchResults();
    }
  }, [params.id, user, isUserLoaded]);

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
  };

  if (!isUserLoaded) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Please sign in to view results
          </h1>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navigation />
        <div className="flex items-center justify-center h-[calc(100vh-4rem)]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-lg text-gray-600">Loading results...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navigation />
        <div className="flex items-center justify-center h-[calc(100vh-4rem)]">
          <div className="text-center">
            <ExclamationTriangleIcon className="h-12 w-12 text-red-500 mx-auto" />
            <p className="mt-4 text-lg text-gray-600">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!result) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      <div className="py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Document Viewer */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Document Preview</h2>
              <div className="border rounded-lg overflow-hidden">
                <Document
                  file={`${process.env.NEXT_PUBLIC_API_URL}/documents/${params.id}`}
                  onLoadSuccess={onDocumentLoadSuccess}
                  className="max-h-[800px] overflow-auto"
                >
                  <Page
                    pageNumber={pageNumber}
                    renderTextLayer={false}
                    renderAnnotationLayer={false}
                  />
                </Document>
              </div>
              {numPages && (
                <div className="mt-4 flex items-center justify-between">
                  <button
                    onClick={() => setPageNumber(page => Math.max(1, page - 1))}
                    disabled={pageNumber <= 1}
                    className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <p className="text-sm text-gray-600">
                    Page {pageNumber} of {numPages}
                  </p>
                  <button
                    onClick={() => setPageNumber(page => Math.min(numPages, page + 1))}
                    disabled={pageNumber >= numPages}
                    className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              )}
            </div>

            {/* Compliance Results */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Compliance Results</h2>
              <div className="space-y-4">
                {result.violations.length === 0 ? (
                  <div className="p-4 bg-green-50 rounded-md">
                    <p className="text-green-700">No compliance violations found!</p>
                  </div>
                ) : (
                  result.violations.map((violation, index) => (
                    <div key={index} className="p-4 bg-red-50 rounded-md">
                      <h3 className="font-medium text-red-800">{violation.rule}</h3>
                      <p className="mt-2 text-sm text-red-600">{violation.explanation}</p>
                      <div className="mt-2">
                        <p className="text-sm font-medium text-gray-700">Violating Text:</p>
                        <p className="text-sm text-gray-600 bg-gray-100 p-2 rounded mt-1">
                          {violation.text}
                        </p>
                      </div>
                      <div className="mt-2">
                        <p className="text-sm font-medium text-gray-700">Suggested Fix:</p>
                        <p className="text-sm text-gray-600 bg-gray-100 p-2 rounded mt-1">
                          {violation.suggestion}
                        </p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 