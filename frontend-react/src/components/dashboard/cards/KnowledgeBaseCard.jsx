import { useState, useEffect, useCallback } from 'react';
import { knowledgeAPI } from '../../../services/api';

export default function KnowledgeBaseCard() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState('search'); // search | upload
  const [uploadMsg, setUploadMsg] = useState('');

  // Load KB stats on mount
  useEffect(() => {
    knowledgeAPI.getStats()
      .then(res => setStats(res.data))
      .catch(() => {});
  }, []);

  const doSearch = useCallback(async (e) => {
    e?.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await knowledgeAPI.search(query.trim());
      setResults(res.data?.results || res.data || []);
    } catch {
      setResults([]);
    }
    setLoading(false);
  }, [query]);

  const handleIngest = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadMsg('Uploading...');
    try {
      await knowledgeAPI.ingest(file);
      setUploadMsg(`✅ "${file.name}" ingested`);
      // Refresh stats
      const s = await knowledgeAPI.getStats();
      setStats(s.data);
    } catch {
      setUploadMsg('❌ Upload failed');
    }
    e.target.value = '';
  };

  const handleDelete = async (docId) => {
    if (!confirm('Delete this document?')) return;
    try {
      await knowledgeAPI.deleteDoc(docId);
      setResults(prev => prev.filter(r => r.id !== docId));
      const s = await knowledgeAPI.getStats();
      setStats(s.data);
    } catch {}
  };

  return (
    <div className="kb-card">
      <div className="kb-header">
        <span className="kb-title">📚 KNOWLEDGE BASE</span>
        {stats && <span className="kb-count">{stats.total_documents ?? stats.count ?? 0} docs</span>}
      </div>

      {/* Tabs */}
      <div className="kb-tabs">
        <button className={`kb-tab ${tab === 'search' ? 'active' : ''}`} onClick={() => setTab('search')}>Search</button>
        <button className={`kb-tab ${tab === 'upload' ? 'active' : ''}`} onClick={() => setTab('upload')}>Upload</button>
      </div>

      {/* Search tab */}
      {tab === 'search' && (
        <>
          <form onSubmit={doSearch} className="kb-search-form">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search knowledge..."
              className="kb-search-input"
            />
            <button type="submit" className="kb-search-btn" disabled={loading}>
              {loading ? '...' : '🔍'}
            </button>
          </form>

          <div className="kb-results">
            {results.length === 0 && query && !loading && (
              <div className="kb-empty">No results found</div>
            )}
            {results.map((item, i) => (
              <div key={item.id || i} className="kb-result-item">
                <div className="kb-result-title">{item.title || item.source || `Result ${i + 1}`}</div>
                <div className="kb-result-text">{(item.content || item.text || '').slice(0, 150)}...</div>
                {item.score && <span className="kb-result-score">{Math.round(item.score * 100)}% match</span>}
                {item.id && (
                  <button className="kb-delete-btn" onClick={() => handleDelete(item.id)} title="Delete">✕</button>
                )}
              </div>
            ))}
          </div>
        </>
      )}

      {/* Upload tab */}
      {tab === 'upload' && (
        <div className="kb-upload">
          <label className="kb-upload-area">
            <input type="file" onChange={handleIngest} accept=".pdf,.txt,.md,.docx,.json,.csv" hidden />
            <div className="kb-upload-icon">📄</div>
            <div className="kb-upload-text">Click to upload document</div>
            <div className="kb-upload-hint">PDF, TXT, MD, DOCX, JSON, CSV</div>
          </label>
          {uploadMsg && <div className="kb-upload-msg">{uploadMsg}</div>}
        </div>
      )}
    </div>
  );
}
