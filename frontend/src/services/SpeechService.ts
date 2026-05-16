/**
 * Сервис для работы с голосовым интерфейсом (TTS/ASR).
 *
 * TTS: использует бэкенд-прокси к Yandex SpeechKit для синтеза речи.
 * ASR: использует Web Speech API (SpeechRecognition) для распознавания речи
 *      в реальном времени прямо в браузере. Это даёт мгновенный результат
 *      без необходимости отправлять аудио на сервер.
 *
 * Fallback: если Web Speech API недоступен, используется MediaRecorder
 *           с отправкой на бэкенд для распознавания через Yandex SpeechKit.
 */

const BASE_URL = '/api/v1/voice';

export interface SpeakOptions {
  voice?: string;
  speed?: number;
}

export interface VoiceStatus {
  tts_available: boolean;
  asr_available: boolean;
  voice: string;
  language: string;
}

// ─── Типы для Web Speech API ───

interface SpeechRecognitionEvent {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognitionErrorEvent {
  error: string;
  message?: string;
}

interface SpeechRecognitionInstance extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  onstart: (() => void) | null;
}

declare global {
  interface Window {
    SpeechRecognition?: new () => SpeechRecognitionInstance;
    webkitSpeechRecognition?: new () => SpeechRecognitionInstance;
  }
}

class SpeechServiceClass {
  private audio: HTMLAudioElement | null = null;
  private mediaRecorder: MediaRecorder | null = null;
  private stream: MediaStream | null = null;
  private recognition: SpeechRecognitionInstance | null = null;
  private _isSpeaking = false;
  private _isListening = false;
  private _status: VoiceStatus | null = null;
  private _webSpeechAvailable = false;

  constructor() {
    // Проверяем доступность Web Speech API
    this._webSpeechAvailable = !!(window.SpeechRecognition || window.webkitSpeechRecognition);
  }

  get isSpeaking(): boolean {
    return this._isSpeaking;
  }

  get isListening(): boolean {
    return this._isListening;
  }

  /** Доступен ли Web Speech API в текущем браузере */
  get webSpeechAvailable(): boolean {
    return this._webSpeechAvailable;
  }

  /**
   * Проверяет доступность голосового интерфейса.
   */
  async getStatus(): Promise<VoiceStatus> {
    if (this._status) return this._status;

    try {
      const res = await fetch(`${BASE_URL}/status`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      this._status = await res.json();
      return this._status!;
    } catch {
      this._status = {
        tts_available: false,
        asr_available: false,
        voice: 'alena',
        language: 'ru-RU',
      };
      return this._status;
    }
  }

  // ──────────────────────── TTS (Синтез речи) ────────────────────────

  /**
   * Синтез речи (TTS) — озвучивает текст через бэкенд.
   */
  async speak(text: string, options: SpeakOptions = {}): Promise<void> {
    // Останавливаем текущее воспроизведение
    this.stopSpeaking();

    const { voice = 'alena', speed = 1.0 } = options;

    try {
      const formData = new FormData();
      formData.append('text', text);
      formData.append('voice', voice);
      formData.append('speed', String(speed));

      const res = await fetch(`${BASE_URL}/tts`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errText = await res.text();
        console.error('TTS error:', errText);
        throw new Error(`Ошибка синтеза речи: ${res.status}`);
      }

      const audioBlob = await res.blob();
      const audioUrl = URL.createObjectURL(audioBlob);

      this.audio = new Audio(audioUrl);
      this._isSpeaking = true;

      return new Promise<void>((resolve, reject) => {
        if (!this.audio) {
          reject(new Error('Аудио не создано'));
          return;
        }

        this.audio.onended = () => {
          this._isSpeaking = false;
          URL.revokeObjectURL(audioUrl);
          resolve();
        };

        this.audio.onerror = () => {
          this._isSpeaking = false;
          URL.revokeObjectURL(audioUrl);
          reject(new Error('Ошибка воспроизведения аудио'));
        };

        this.audio.play().catch((err) => {
          this._isSpeaking = false;
          URL.revokeObjectURL(audioUrl);
          reject(err);
        });
      });
    } catch (error) {
      this._isSpeaking = false;
      throw error;
    }
  }

  /**
   * Останавливает текущее воспроизведение речи.
   */
  stopSpeaking(): void {
    if (this.audio) {
      this.audio.pause();
      this.audio.currentTime = 0;
      this.audio = null;
    }
    this._isSpeaking = false;
  }

  // ──────────────────────── ASR (Распознавание речи) ────────────────────────

  /**
   * Начинает прослушивание через Web Speech API (основной метод).
   * Работает в реальном времени — распознаёт речь по мере говорения.
   * Результат вызывается через onTranscript при каждом распознанном фрагменте.
   */
  async startListening(
    onTranscript: (text: string, isFinal: boolean) => void,
    onError?: (error: Error) => void,
  ): Promise<void> {
    // Принудительно останавливаем предыдущую сессию,
    // чтобы избежать залипания флага _isListening
    if (this._isListening) {
      this.stopListening();
    }

    // ─── Приоритет: Web Speech API ───
    if (this._webSpeechAvailable) {
      return this._startWebSpeechListening(onTranscript, onError);
    }

    // ─── Fallback: MediaRecorder + бэкенд ASR ───
    return this._startMediaRecorderListening(onTranscript, onError);
  }

  /**
   * Останавливает прослушивание.
   */
  stopListening(): void {
    // Web Speech API
    if (this.recognition) {
      this.recognition.stop();
      this.recognition = null;
    }

    // MediaRecorder fallback
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    }

    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
      this.stream = null;
    }

    this._isListening = false;
  }

  /**
   * Полная отмена — останавливает и воспроизведение, и запись.
   */
  cancel(): void {
    this.stopSpeaking();
    this.stopListening();
  }

  // ──────────────────────── Web Speech API ────────────────────────

  private async _startWebSpeechListening(
    onTranscript: (text: string, isFinal: boolean) => void,
    onError?: (error: Error) => void,
  ): Promise<void> {
    const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognitionCtor) {
      console.warn('[SpeechService] Web Speech API недоступен, пробуем MediaRecorder fallback');
      return this._startMediaRecorderListening(onTranscript, onError);
    }

    // ─── Явный запрос доступа к микрофону ───
    // Это гарантирует, что браузер покажет диалог разрешения
    try {
      console.log('[SpeechService] Запрашиваю доступ к микрофону...');
      const micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // Сразу освобождаем поток — SpeechRecognition запросит сам
      micStream.getTracks().forEach(t => t.stop());
      console.log('[SpeechService] Доступ к микрофону получен');
    } catch (micErr) {
      console.error('[SpeechService] Нет доступа к микрофону:', micErr);
      this._isListening = false;
      if (onError) onError(new Error('Нет доступа к микрофону. Разрешите доступ в настройках браузера.'));
      return;
    }

    this.recognition = new SpeechRecognitionCtor();
    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.recognition.lang = 'ru-RU';
    this.recognition.maxAlternatives = 1;

    this._isListening = true;

    this.recognition.onstart = () => {
      console.log('[SpeechService] Web Speech: прослушивание начато');
    };

    this.recognition.onresult = (event: SpeechRecognitionEvent) => {
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        const transcript = result[0].transcript;
        const isFinal = result.isFinal;

        if (transcript) {
          console.log('[SpeechService] Распознано:', transcript, isFinal ? '(финальный)' : '(промежуточный)');
          onTranscript(transcript, isFinal);
        }
      }
    };

    this.recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      console.error('[SpeechService] Web Speech error:', event.error, event.message);

      // 'no-speech' — не ошибка, просто тишина
      if (event.error === 'no-speech') return;

      // 'aborted' — мы сами остановили
      if (event.error === 'aborted') return;

      // 'network' — временная сетевая ошибка, не мешает работе
      if (event.error === 'network') return;

      // 'not-allowed' — нет разрешения на микрофон
      if (event.error === 'not-allowed') {
        this._isListening = false;
        if (onError) onError(new Error('Нет разрешения на микрофон. Разрешите доступ в настройках браузера.'));
        return;
      }

      this._isListening = false;
      if (onError) {
        onError(new Error(`Ошибка распознавания: ${event.error}`));
      }
    };

    this.recognition.onend = () => {
      console.log('[SpeechService] Web Speech: прослушивание завершено');
      // Если мы всё ещё хотим слушать (не вызывали stop), перезапускаем
      if (this._isListening && this.recognition) {
        try {
          this.recognition.start();
        } catch {
          this._isListening = false;
        }
      }
    };

    try {
      this.recognition.start();
      console.log('[SpeechService] recognition.start() вызван');
    } catch (err) {
      console.error('[SpeechService] Ошибка при recognition.start():', err);
      this._isListening = false;
      if (onError) onError(new Error('Не удалось запустить распознавание речи'));
    }
  }

  // ──────────────────────── MediaRecorder fallback ────────────────────────

  private async _startMediaRecorderListening(
    onTranscript: (text: string, isFinal: boolean) => void,
    onError?: (error: Error) => void,
  ): Promise<void> {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      this._isListening = true;

      const mimeType = MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')
        ? 'audio/ogg;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : 'audio/webm';

      this.mediaRecorder = new MediaRecorder(this.stream, { mimeType });

      const chunks: BlobPart[] = [];

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };

      this.mediaRecorder.onstop = async () => {
        this._isListening = false;

        const audioBlob = new Blob(chunks, { type: mimeType });

        try {
          const formData = new FormData();
          formData.append('audio', audioBlob, 'recording.ogg');
          formData.append('language', 'ru-RU');

          const res = await fetch(`${BASE_URL}/asr`, {
            method: 'POST',
            body: formData,
          });

          if (!res.ok) throw new Error(`Ошибка распознавания: ${res.status}`);

          const data = await res.json();
          if (data.error) throw new Error(data.error);
          if (data.text) {
            onTranscript(data.text, true);
          }
        } catch (err) {
          console.error('[SpeechService] ASR fallback error:', err);
          if (onError) {
            onError(err instanceof Error ? err : new Error(String(err)));
          }
        }

        if (this.stream) {
          this.stream.getTracks().forEach((track) => track.stop());
          this.stream = null;
        }
      };

      this.mediaRecorder.onerror = (event) => {
        this._isListening = false;
        console.error('[SpeechService] MediaRecorder error:', event);
        if (onError) onError(new Error('Ошибка записи аудио'));
      };

      // Записываем 5 секунд, потом отправляем на распознавание
      this.mediaRecorder.start();
      setTimeout(() => {
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
          this.mediaRecorder.stop();
        }
      }, 5000);
    } catch (err) {
      this._isListening = false;
      console.error('[SpeechService] Microphone access error:', err);
      if (onError) {
        onError(err instanceof Error ? err : new Error('Не удалось получить доступ к микрофону'));
      }
    }
  }
}

// Экспортируем singleton
export const SpeechService = new SpeechServiceClass();
