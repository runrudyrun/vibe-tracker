#!/usr/bin/env python3
"""
Performance Bottleneck Test for Vibe-Tracker Audio Lag Investigation

This test measures the specific bottlenecks identified in the code analysis:
1. Inefficient sample generation (next() calls in loops)
2. Excessive logging overhead in audio callbacks
3. Memory allocation pressure
4. Linear note processing scaling
5. Note accumulation over time

Run from the root directory: python3 performance_bottleneck_test.py
"""

import sys
import os
import time
import numpy as np
import logging
from typing import List, Dict
import gc

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import without relative imports by running as module
import importlib.util

def load_module(name, path):
    """Load a module from a file path."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

# Load modules
src_dir = os.path.join(os.path.dirname(__file__), '..', 'src')
music_structures = load_module('music_structures', os.path.join(src_dir, 'music_structures.py'))
synthesis = load_module('synthesis', os.path.join(src_dir, 'synthesis.py'))

# Aliases for easier use
Composition = music_structures.Composition
Track = music_structures.Track  
Pattern = music_structures.Pattern
NoteEvent = music_structures.NoteEvent
Instrument = synthesis.Instrument
SAMPLE_RATE = synthesis.SAMPLE_RATE

class PerformanceProfiler:
    """Measures performance of specific operations."""
    
    def __init__(self):
        self.results = {}
        
    def time_operation(self, name: str, operation_func, iterations: int = 1):
        """Time an operation and return average time per iteration."""
        times = []
        
        for i in range(iterations):
            start_time = time.perf_counter()
            result = operation_func()
            end_time = time.perf_counter()
            times.append(end_time - start_time)
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        self.results[name] = {
            'avg_time_ms': avg_time * 1000,
            'min_time_ms': min_time * 1000,
            'max_time_ms': max_time * 1000,
            'iterations': iterations,
            'total_time_ms': sum(times) * 1000
        }
        
        print(f"{name}: {avg_time*1000:.3f}ms avg ({min_time*1000:.3f}-{max_time*1000:.3f}ms range)")
        return result

def test_sample_generation_bottleneck():
    """Test the inefficient next() call pattern vs vectorized generation."""
    print("\n=== TESTING SAMPLE GENERATION BOTTLENECK ===")
    
    profiler = PerformanceProfiler()
    
    # Create a sine wave generator (current inefficient method)
    def create_sine_generator(frequency):
        increment = (2 * np.pi * frequency) / SAMPLE_RATE
        phase = 0
        while True:
            yield np.sin(phase)
            phase += increment
    
    # Test current inefficient method
    generator = create_sine_generator(440)  # A4
    num_samples = 1024  # Typical audio buffer size
    
    def inefficient_generation():
        return np.array([next(generator) for _ in range(num_samples)])
    
    # Test vectorized method
    def vectorized_generation():
        phase_increment = (2 * np.pi * 440) / SAMPLE_RATE
        phases = np.arange(num_samples) * phase_increment
        return np.sin(phases)
    
    print(f"Generating {num_samples} samples at 440Hz:")
    
    # Time both methods
    inefficient_result = profiler.time_operation("Inefficient (current)", inefficient_generation, 100)
    vectorized_result = profiler.time_operation("Vectorized (optimized)", vectorized_generation, 100)
    
    # Calculate speedup
    speedup = profiler.results["Inefficient (current)"]["avg_time_ms"] / profiler.results["Vectorized (optimized)"]["avg_time_ms"]
    print(f"Vectorized method is {speedup:.1f}x faster")
    
    return profiler.results

def test_logging_overhead():
    """Test the overhead of debug logging in audio callbacks."""
    print("\n=== TESTING LOGGING OVERHEAD ===")
    
    profiler = PerformanceProfiler()
    
    # Setup logger
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.DEBUG)
    
    # Create a handler that actually processes the logs
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    
    # Test with logging
    def with_logging():
        for i in range(100):  # Simulate processing 100 notes
            logger.debug(f"Processing note {i}: C4, is_active: True")
            logger.debug(f"Note {i} processed successfully")
    
    # Test without logging
    def without_logging():
        for i in range(100):  # Same loop, no logging
            pass
    
    # Disable logging for comparison
    logger.setLevel(logging.CRITICAL)
    
    print("Processing 100 notes with/without debug logging:")
    
    # Enable logging for test
    logger.setLevel(logging.DEBUG)
    with_log_result = profiler.time_operation("With Debug Logging", with_logging, 50)
    
    # Disable logging for test
    logger.setLevel(logging.CRITICAL)
    without_log_result = profiler.time_operation("Without Logging", without_logging, 50)
    
    # Calculate overhead
    overhead = profiler.results["With Debug Logging"]["avg_time_ms"] - profiler.results["Without Logging"]["avg_time_ms"]
    print(f"Logging adds {overhead:.3f}ms overhead per 100 operations")
    
    # Clean up
    logger.removeHandler(handler)
    
    return profiler.results

def test_memory_allocation_pressure():
    """Test memory allocation patterns in audio processing."""
    print("\n=== TESTING MEMORY ALLOCATION PRESSURE ===")
    
    profiler = PerformanceProfiler()
    
    num_samples = 1024
    
    # Test current pattern: allocate new arrays every time
    def allocate_every_time():
        buffers = []
        for i in range(10):  # Simulate 10 instruments
            buffer = np.zeros(num_samples)  # New allocation
            buffer += np.random.random(num_samples)  # More allocation
            buffers.append(buffer)
        return sum(buffers)  # Final allocation
    
    # Test optimized pattern: reuse buffers
    def reuse_buffers():
        # Create buffers inside function to avoid scope issues
        reused_buffer = np.zeros(num_samples)
        temp_buffer = np.zeros(num_samples)
        
        for i in range(10):  # Simulate 10 instruments
            temp_buffer[:] = np.random.random(num_samples)  # Fill temp buffer
            reused_buffer += temp_buffer  # In-place addition
        return reused_buffer
    
    print(f"Processing 10 instruments with {num_samples} samples each:")
    
    # Measure memory allocations
    gc.collect()  # Clean start
    mem_before = len(gc.get_objects())
    
    alloc_result = profiler.time_operation("Allocate Every Time", allocate_every_time, 100)
    
    mem_after_alloc = len(gc.get_objects())
    
    reuse_result = profiler.time_operation("Reuse Buffers", reuse_buffers, 100)
    
    mem_after_reuse = len(gc.get_objects())
    
    print(f"Objects created - Allocate: {mem_after_alloc - mem_before}, Reuse: {mem_after_reuse - mem_after_alloc}")
    
    return profiler.results

def test_note_processing_scaling():
    """Test how note processing scales with number of active notes."""
    print("\n=== TESTING NOTE PROCESSING SCALING ===")
    
    profiler = PerformanceProfiler()
    
    # Create test instruments with varying numbers of active notes
    def create_test_instrument(num_notes: int):
        instrument = Instrument(
            name=f"test_{num_notes}",
            oscillators=[{'waveform': 'sine', 'amplitude': 0.1}],
            attack=0.01, decay=0.1, sustain_level=0.7, release=0.2
        )
        
        # Add active notes
        for i in range(num_notes):
            note_name = f"C{4 + (i % 2)}"
            instrument.note_on(note_name, 0.5)
        
        return instrument
    
    # Test different numbers of active notes
    note_counts = [1, 5, 10, 20, 50]
    results = {}
    
    for count in note_counts:
        instrument = create_test_instrument(count)
        
        def process_instrument():
            return instrument.process(1024)
        
        print(f"Processing instrument with {count} active notes:")
        result = profiler.time_operation(f"{count} Notes", process_instrument, 20)
        results[count] = profiler.results[f"{count} Notes"]["avg_time_ms"]
    
    # Analyze scaling
    print("\nScaling analysis:")
    for i, count in enumerate(note_counts[1:], 1):
        prev_count = note_counts[i-1]
        time_ratio = results[count] / results[prev_count]
        note_ratio = count / prev_count
        print(f"{prev_count} -> {count} notes: {time_ratio:.2f}x time increase ({note_ratio:.1f}x notes)")
    
    return results

def test_note_accumulation_simulation():
    """Simulate note accumulation over time."""
    print("\n=== TESTING NOTE ACCUMULATION SIMULATION ===")
    
    profiler = PerformanceProfiler()
    
    # Create instrument
    instrument = Instrument(
        name="accumulation_test",
        oscillators=[{'waveform': 'sine', 'amplitude': 0.1}],
        attack=0.01, decay=0.1, sustain_level=0.7, release=0.5  # Longer release
    )
    
    note_counts = []
    processing_times = []
    
    print("Simulating note accumulation over time:")
    
    # Simulate 30 seconds of playback at 120 BPM (2 beats per second)
    for second in range(30):
        # Add 2 notes per second (simulating beat triggers)
        for beat in range(2):
            note_name = f"C{4 + ((second * 2 + beat) % 3)}"
            instrument.note_on(note_name, 0.5)
        
        # Sometimes turn off notes (simulating note_off events)
        if second % 3 == 0 and instrument.active_notes:
            # Turn off oldest note
            oldest_note = instrument.active_notes[0]
            instrument.note_off(oldest_note.note_name)
        
        # Measure processing time
        start_time = time.perf_counter()
        instrument.process(1024)
        processing_time = (time.perf_counter() - start_time) * 1000
        
        active_count = len(instrument.active_notes)
        note_counts.append(active_count)
        processing_times.append(processing_time)
        
        if second % 5 == 0:  # Report every 5 seconds
            print(f"Second {second}: {active_count} active notes, {processing_time:.3f}ms processing")
    
    # Analysis
    max_notes = max(note_counts)
    final_notes = note_counts[-1]
    avg_processing = sum(processing_times) / len(processing_times)
    max_processing = max(processing_times)
    
    print(f"\nAccumulation results:")
    print(f"Max active notes: {max_notes}")
    print(f"Final active notes: {final_notes}")
    print(f"Average processing time: {avg_processing:.3f}ms")
    print(f"Max processing time: {max_processing:.3f}ms")
    
    # Check for accumulation trend
    early_avg = sum(note_counts[:10]) / 10
    late_avg = sum(note_counts[-10:]) / 10
    
    if late_avg > early_avg * 1.5:
        print("⚠️  NOTE ACCUMULATION DETECTED - Notes growing over time")
    else:
        print("✅ Note count appears stable")
    
    return {
        'max_notes': max_notes,
        'final_notes': final_notes,
        'avg_processing_ms': avg_processing,
        'max_processing_ms': max_processing,
        'note_counts': note_counts,
        'processing_times': processing_times
    }

def main():
    """Run all performance bottleneck tests."""
    print("=== VIBE-TRACKER PERFORMANCE BOTTLENECK INVESTIGATION ===")
    print("Testing specific bottlenecks identified in code analysis:")
    print("1. Sample generation efficiency")
    print("2. Logging overhead in audio callbacks")
    print("3. Memory allocation pressure")
    print("4. Note processing scaling")
    print("5. Note accumulation over time")
    print()
    
    all_results = {}
    
    try:
        # Run all tests
        all_results['sample_generation'] = test_sample_generation_bottleneck()
        all_results['logging_overhead'] = test_logging_overhead()
        all_results['memory_allocation'] = test_memory_allocation_pressure()
        all_results['note_scaling'] = test_note_processing_scaling()
        all_results['note_accumulation'] = test_note_accumulation_simulation()
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
        all_results['error'] = str(e)
    
    # Generate summary
    print("\n" + "="*60)
    print("PERFORMANCE BOTTLENECK SUMMARY")
    print("="*60)
    
    print("\n🔍 KEY FINDINGS:")
    
    if 'sample_generation' in all_results:
        sg = all_results['sample_generation']
        if 'Inefficient (current)' in sg and 'Vectorized (optimized)' in sg:
            speedup = sg['Inefficient (current)']['avg_time_ms'] / sg['Vectorized (optimized)']['avg_time_ms']
            print(f"• Sample generation: Vectorization provides {speedup:.1f}x speedup")
    
    if 'logging_overhead' in all_results:
        lo = all_results['logging_overhead']
        if 'With Debug Logging' in lo and 'Without Logging' in lo:
            overhead = lo['With Debug Logging']['avg_time_ms'] - lo['Without Logging']['avg_time_ms']
            print(f"• Logging overhead: {overhead:.3f}ms per 100 operations")
    
    if 'note_accumulation' in all_results:
        na = all_results['note_accumulation']
        print(f"• Note accumulation: Max {na['max_notes']} notes, final {na['final_notes']} notes")
        if na['final_notes'] > 10:
            print("  ⚠️  Notes may be accumulating over time")
    
    # Save results
    import json
    with open('performance_bottleneck_results.json', 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\n📊 Detailed results saved to: performance_bottleneck_results.json")
    
    # Generate data-driven recommendations
    print("\n🎯 RECOMMENDATIONS BASED ON TEST RESULTS:")
    recommendations = []
    
    # Sample generation analysis
    if 'sample_generation' in all_results:
        sg = all_results['sample_generation']
        if 'Inefficient (current)' in sg and 'Vectorized (optimized)' in sg:
            speedup = sg['Inefficient (current)']['avg_time_ms'] / sg['Vectorized (optimized)']['avg_time_ms']
            if speedup > 10:  # Significant speedup
                recommendations.append(f"HIGH PRIORITY: Vectorize sample generation ({speedup:.1f}x speedup potential)")
    
    # Logging overhead analysis
    if 'logging_overhead' in all_results:
        lo = all_results['logging_overhead']
        if 'With Debug Logging' in lo and 'Without Logging' in lo:
            overhead = lo['With Debug Logging']['avg_time_ms'] - lo['Without Logging']['avg_time_ms']
            if overhead > 1.0:  # More than 1ms overhead
                recommendations.append(f"HIGH PRIORITY: Remove debug logging from audio callbacks ({overhead:.1f}ms overhead)")
    
    # Memory allocation analysis
    if 'memory_allocation' in all_results:
        ma = all_results['memory_allocation']
        if 'Allocate Every Time' in ma and 'Reuse Buffers' in ma:
            speedup = ma['Allocate Every Time']['avg_time_ms'] / ma['Reuse Buffers']['avg_time_ms']
            if speedup > 1.5:
                recommendations.append(f"MEDIUM PRIORITY: Implement buffer reuse ({speedup:.1f}x speedup)")
    
    # Note scaling analysis
    if 'note_scaling' in all_results:
        ns = all_results['note_scaling']
        # Check if processing time grows non-linearly with note count
        note_counts = sorted(ns.keys())
        if len(note_counts) >= 3:
            first_time = ns[note_counts[0]]
            last_time = ns[note_counts[-1]]
            note_ratio = note_counts[-1] / note_counts[0]
            time_ratio = last_time / first_time
            if time_ratio > note_ratio * 1.5:  # Non-linear scaling
                recommendations.append(f"MEDIUM PRIORITY: Optimize note processing (non-linear scaling detected)")
    
    # Note accumulation analysis
    if 'note_accumulation' in all_results:
        na = all_results['note_accumulation']
        if na['final_notes'] > na.get('expected_notes', 5):  # More notes than expected
            recommendations.append(f"HIGH PRIORITY: Fix note cleanup (accumulation detected: {na['final_notes']} final notes)")
    
    # Print recommendations or indicate incomplete data
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
    else:
        print("⚠️  Insufficient test data to generate specific recommendations")
        print("   Some tests may have failed - check error messages above")

if __name__ == "__main__":
    main()
