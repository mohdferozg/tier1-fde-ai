import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, HttpClientModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  title = 'CV Analyzer';
  selectedFile: File | null = null;
  loading = false;
  result: any = null;
  error: string | null = null;

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.selectedFile = input.files[0];
      this.error = null;
      this.result = null;
    }
  }

  async uploadCv() {
    if (!this.selectedFile) {
      this.error = 'Please select a PDF file first.';
      return;
    }

    this.loading = true;
    this.error = null;
    this.result = null;

    const formData = new FormData();
    formData.append('file', this.selectedFile);

    try {
      const response = await fetch('https://cv-analyzer-api-rbgc.onrender.com/cv-analysis', {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (!response.ok) {
        this.error = data.detail || `Error: ${response.status}`;
      } else {
        this.result = data;
      }
    } catch (err: any) {
      this.error = `Network error: ${err.message}`;
    } finally {
      this.loading = false;
    }
  }
}