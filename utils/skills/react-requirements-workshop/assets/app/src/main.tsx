import React from 'react'
import { createRoot } from 'react-dom/client'
import Snapshot from './snapshots/001-initial'
import metadata from '../discussion/001-initial.json'
import { Review } from './review/Review'
import './index.css'
import './review/review.css'

createRoot(document.getElementById('root')!).render(<Review key={`${metadata.snapshot.number}-${metadata.snapshot.slug}`} metadata={metadata}><Snapshot /></Review>)
