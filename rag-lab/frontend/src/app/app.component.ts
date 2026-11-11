import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

interface ChunkInfo {
  id: number;
  similarity: number;
}

interface RagResponse {
  answer: string;
  sources: number[];
  chunks: ChunkInfo[];
}

interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
  sources?: number[];
  isLoading?: boolean;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  title = 'RAG Chat';
  query: string = '';
  messages: ChatMessage[] = [];
  loading = false;

  async sendQuery() {
    if (!this.query.trim() || this.loading) return;

    const userText = this.query.trim();
    
    // Add user message
    this.messages.push({ role: 'user', text: userText });
    
    // Clear input
    this.query = '';
    
    // Add loading assistant message
    const loadingMsg: ChatMessage = { role: 'assistant', text: '', isLoading: true };
    this.messages.push(loadingMsg);
    this.loading = true;

    try {
      const response = await fetch('http://127.0.0.1:8000/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userText, top_k: 3 })
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data: RagResponse = await response.json();
      
      // Replace loading message with real answer
      loadingMsg.text = data.answer;
      loadingMsg.sources = data.sources;
      loadingMsg.isLoading = false;

    } catch (err: any) {
      loadingMsg.text = `Error: ${err.message}`;
      loadingMsg.isLoading = false;
    } finally {
      this.loading = false;
    }
  }
}