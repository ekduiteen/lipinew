/**
 * Vocal Processor — AudioWorklet implementation for glitch-free recording on Android.
 * Runs on a high-priority audio thread.
 */

class VocalProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._chunkSize = 4096;
    this._buffer = new Float32Array(this._chunkSize);
    this._offset = 0;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (!input || !input[0]) return true;

    const channelData = input[0];
    
    // We want to send chunks of 4096 samples to match the existing logic
    for (let i = 0; i < channelData.length; i++) {
      this._buffer[this._offset++] = channelData[i];
      
      if (this._offset >= this._chunkSize) {
        // Send complete chunk back to main thread
        this.port.postMessage(this._buffer);
        this._buffer = new Float32Array(this._chunkSize);
        this._offset = 0;
      }
    }

    return true;
  }
}

registerProcessor('vocal-processor', VocalProcessor);
