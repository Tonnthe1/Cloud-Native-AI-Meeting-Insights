#!/usr/bin/env python3
"""
Measure real-time factor for faster-whisper transcription
Real-time factor = processing_time / audio_duration
Values < 1.0 indicate faster-than-real-time processing
"""

import os
import sys
import time
import tempfile
import subprocess
from pathlib import Path
from typing import Tuple

# Add the backend app directory to path for imports
backend_path = Path(__file__).parent.parent / "backend" / "app"
sys.path.append(str(backend_path))

try:
    from faster_whisper import WhisperModel
    import pydub
except ImportError as e:
    print(f"❌ Required libraries not found: {e}")
    print("💡 Install with: pip install faster-whisper pydub")
    sys.exit(1)

def create_test_audio(duration_seconds: int = 30, sample_rate: int = 16000) -> Path:
    """Create a test audio file for benchmarking."""
    import numpy as np
    
    # Generate a simple sine wave with some noise
    t = np.linspace(0, duration_seconds, duration_seconds * sample_rate, False)
    
    # Mix of frequencies to simulate speech-like audio
    audio = (
        0.3 * np.sin(2 * np.pi * 440 * t) +      # A4 note
        0.2 * np.sin(2 * np.pi * 880 * t) +      # A5 note  
        0.1 * np.random.normal(0, 0.1, len(t))   # Background noise
    )
    
    # Normalize to 16-bit range
    audio = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
    
    # Create temporary WAV file
    temp_dir = Path(tempfile.gettempdir())
    audio_file = temp_dir / f"test_audio_{duration_seconds}s.wav"
    
    # Use pydub to create WAV file
    audio_segment = pydub.AudioSegment(
        audio.tobytes(), 
        frame_rate=sample_rate,
        sample_width=2,  # 16-bit
        channels=1       # Mono
    )
    
    audio_segment.export(str(audio_file), format="wav")
    print(f"📁 Created test audio: {audio_file} ({duration_seconds}s)")
    
    return audio_file

def get_audio_duration(file_path: Path) -> float:
    """Get audio duration in seconds."""
    try:
        audio = pydub.AudioSegment.from_file(str(file_path))
        return len(audio) / 1000.0  # Convert ms to seconds
    except Exception as e:
        print(f"❌ Error getting audio duration: {e}")
        return 0.0

def test_faster_whisper_performance(audio_file: Path, model_name: str = "base.en") -> Tuple[float, float, str]:
    """
    Test faster-whisper performance and calculate real-time factor.
    Returns: (processing_time, audio_duration, real_time_factor)
    """
    print(f"🤖 Loading {model_name} model...")
    
    # Load model
    model_load_start = time.time()
    model = WhisperModel(model_name, device="cpu", compute_type="float32")
    model_load_time = time.time() - model_load_start
    
    print(f"✅ Model loaded in {model_load_time:.2f}s")
    
    # Get audio duration
    audio_duration = get_audio_duration(audio_file)
    print(f"🎵 Audio duration: {audio_duration:.2f}s")
    
    # Transcribe
    print("🎙️  Starting transcription...")
    transcribe_start = time.time()
    
    segments, info = model.transcribe(
        str(audio_file),
        beam_size=5,
        vad_filter=True,
    )
    
    # Process all segments to get full processing time
    transcript_parts = [segment.text for segment in segments]
    transcript = " ".join(transcript_parts).strip()
    
    processing_time = time.time() - transcribe_start
    
    print(f"⏱️  Processing time: {processing_time:.2f}s")
    print(f"📝 Transcript length: {len(transcript)} characters")
    print(f"🌐 Detected language: {getattr(info, 'language', 'unknown')}")
    
    # Calculate real-time factor
    real_time_factor = processing_time / audio_duration if audio_duration > 0 else float('inf')
    
    return processing_time, audio_duration, real_time_factor, transcript

def run_performance_test(test_durations: list = [10, 30, 60], model_name: str = "base.en"):
    """Run performance tests with different audio durations."""
    print("🚀 Starting faster-whisper performance measurement")
    print("=" * 60)
    
    results = []
    
    for duration in test_durations:
        print(f"\n📊 Testing with {duration}s audio...")
        print("-" * 40)
        
        # Create test audio
        audio_file = create_test_audio(duration)
        
        try:
            # Run transcription test
            processing_time, audio_duration, rtf, transcript = test_faster_whisper_performance(
                audio_file, model_name
            )
            
            results.append({
                'duration': audio_duration,
                'processing_time': processing_time,
                'real_time_factor': rtf,
                'transcript_length': len(transcript)
            })
            
            # Display results
            print(f"📈 Real-time factor: {rtf:.3f}")
            
            if rtf < 1.0:
                speed_multiplier = 1.0 / rtf
                print(f"🏃 Processing speed: {speed_multiplier:.1f}× faster than real-time")
                if speed_multiplier >= 2.0:
                    print("🎯 ✅ Achieves 2× real-time speed target!")
                else:
                    print(f"⚠️  Below 2× target (current: {speed_multiplier:.1f}×)")
            else:
                print("🐌 Processing slower than real-time")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            results.append({
                'duration': duration,
                'processing_time': 0,
                'real_time_factor': float('inf'),
                'transcript_length': 0,
                'error': str(e)
            })
        
        finally:
            # Clean up test file
            if audio_file.exists():
                audio_file.unlink()
    
    return results

def generate_performance_report(results: list, model_name: str):
    """Generate a performance report."""
    print("\n" + "=" * 60)
    print("📋 PERFORMANCE SUMMARY REPORT")
    print("=" * 60)
    
    print(f"🤖 Model: {model_name}")
    print(f"💻 Device: CPU (float32)")
    print(f"📅 Test date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    successful_tests = [r for r in results if 'error' not in r]
    
    if not successful_tests:
        print("❌ No successful tests completed")
        return
    
    print(f"\n📊 Test Results ({len(successful_tests)} successful tests):")
    print("-" * 60)
    
    for i, result in enumerate(successful_tests):
        rtf = result['real_time_factor']
        speed = 1.0 / rtf if rtf > 0 else 0
        
        print(f"Test {i+1}: {result['duration']:.1f}s audio")
        print(f"  Processing time: {result['processing_time']:.2f}s")
        print(f"  Real-time factor: {rtf:.3f}")
        print(f"  Speed multiplier: {speed:.1f}×")
        print(f"  Transcript length: {result['transcript_length']} chars")
        print()
    
    # Calculate averages
    avg_rtf = sum(r['real_time_factor'] for r in successful_tests) / len(successful_tests)
    avg_speed = 1.0 / avg_rtf if avg_rtf > 0 else 0
    
    print(f"📈 Average Performance:")
    print(f"  Real-time factor: {avg_rtf:.3f}")
    print(f"  Speed multiplier: {avg_speed:.1f}×")
    
    # Check targets
    print(f"\n🎯 Performance Targets:")
    if avg_speed >= 2.0:
        print(f"  ✅ 2× real-time speed: ACHIEVED ({avg_speed:.1f}×)")
    else:
        print(f"  ❌ 2× real-time speed: NOT ACHIEVED ({avg_speed:.1f}×)")
    
    if avg_rtf < 1.0:
        print(f"  ✅ Faster than real-time: YES")
    else:
        print(f"  ❌ Faster than real-time: NO")
    
    # Save report
    report_file = Path("docs/realtime_factor_report.txt")
    report_file.parent.mkdir(exist_ok=True)
    
    with open(report_file, 'w') as f:
        f.write(f"# Faster-Whisper Real-time Factor Report\n\n")
        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Model: {model_name}\n")
        f.write(f"Device: CPU (float32)\n\n")
        f.write(f"## Results\n\n")
        
        for i, result in enumerate(successful_tests):
            rtf = result['real_time_factor']
            speed = 1.0 / rtf if rtf > 0 else 0
            f.write(f"Test {i+1} ({result['duration']:.1f}s audio):\n")
            f.write(f"- Processing time: {result['processing_time']:.2f}s\n")
            f.write(f"- Real-time factor: {rtf:.3f}\n")
            f.write(f"- Speed multiplier: {speed:.1f}×\n\n")
        
        f.write(f"## Summary\n\n")
        f.write(f"Average real-time factor: {avg_rtf:.3f}\n")
        f.write(f"Average speed multiplier: {avg_speed:.1f}×\n\n")
        
        if avg_speed >= 2.0:
            f.write("✅ **CONCLUSION: Achieves 2× faster than real-time processing**\n")
        else:
            f.write(f"⚠️ **CONCLUSION: Processing speed {avg_speed:.1f}× (below 2× target)**\n")
    
    print(f"\n💾 Report saved to: {report_file}")

def main():
    """Main function."""
    model_name = os.getenv("FW_MODEL", "base.en")
    
    print("⚡ Faster-Whisper Real-time Factor Measurement")
    print(f"🤖 Model: {model_name}")
    print(f"💻 Device: CPU")
    
    # Run tests with different durations
    results = run_performance_test([10, 30, 60], model_name)
    
    # Generate report
    generate_performance_report(results, model_name)

if __name__ == "__main__":
    main()