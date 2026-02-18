"""
Tests for AI Engine with MLX Optimization
"""

import pytest
import asyncio
from cell0.cell0.engine.ai_engine import (
    AIEngine,
    ModelConfig,
    ModelPrecision,
    TPVResonance,
    ModelQuantizer,
    MultiModelConsensus,
)


@pytest.mark.asyncio
async def test_ai_engine_initialization():
    """Test AI engine initialization"""
    engine = AIEngine()
    await engine.initialize()
    
    info = engine.get_system_info()
    assert "mlx_available" in info
    assert "models_loaded" in info
    assert isinstance(info["models_loaded"], list)


@pytest.mark.asyncio
async def test_model_config():
    """Test model configuration"""
    config = ModelConfig(
        model_id="test-model",
        precision=ModelPrecision.FP16,
        max_tokens=1024,
        temperature=0.8,
    )
    
    assert config.model_id == "test-model"
    assert config.precision == ModelPrecision.FP16
    assert config.max_tokens == 1024
    assert config.temperature == 0.8


@pytest.mark.asyncio
async def test_tpv_resonance():
    """Test TPV resonance calculation"""
    tpv = TPVResonance(
        thought_weight=1.0,
        preference_weight=0.8,
        value_weight=0.6,
    )
    
    # Test with dummy embeddings
    thought = [0.1, 0.2, 0.3, 0.4, 0.5]
    preference = [0.15, 0.25, 0.35, 0.45, 0.55]
    value = [0.12, 0.22, 0.32, 0.42, 0.52]
    
    resonance = tpv.calculate_resonance(thought, preference, value)
    
    # Resonance should be between -1 and 1
    assert -1.0 <= resonance <= 1.0


@pytest.mark.asyncio
async def test_model_quantizer():
    """Test model quantization"""
    quantizer = ModelQuantizer()
    
    # Test memory estimation
    mem_fp32 = quantizer.estimate_memory_usage(7_000_000_000, ModelPrecision.FP32)
    mem_fp16 = quantizer.estimate_memory_usage(7_000_000_000, ModelPrecision.FP16)
    mem_int8 = quantizer.estimate_memory_usage(7_000_000_000, ModelPrecision.INT8)
    
    # FP16 should use half the memory of FP32
    assert mem_fp16 == mem_fp32 / 2
    # INT8 should use quarter the memory of FP32
    assert mem_int8 == mem_fp32 / 4


@pytest.mark.asyncio
async def test_multi_model_consensus():
    """Test multi-model consensus"""
    consensus = MultiModelConsensus()
    
    # Create mock models
    config1 = ModelConfig(model_id="model-1", precision=ModelPrecision.FP16)
    config2 = ModelConfig(model_id="model-2", precision=ModelPrecision.FP16)
    
    model1 = ModelQuantizer()  # Using as placeholder
    model2 = ModelQuantizer()
    
    # In production, these would be MLXModel instances
    # For now, just verify the consensus structure exists
    assert consensus is not None


@pytest.mark.asyncio
async def test_generate_without_models():
    """Test that generation fails without loaded models"""
    engine = AIEngine()
    await engine.initialize()
    
    with pytest.raises(RuntimeError, match="No models loaded"):
        await engine.generate("Test prompt")


@pytest.mark.skipif(True, reason="Requires MLX installation")
@pytest.mark.asyncio
async def test_mlx_model_loading():
    """Test MLX model loading (requires MLX)"""
    engine = AIEngine()
    await engine.initialize()
    
    config = ModelConfig(
        model_id="test-model",
        precision=ModelPrecision.FP16,
    )
    
    result = await engine.load_model(config)
    assert result is True
    assert "test-model" in engine.get_system_info()["models_loaded"]


@pytest.mark.asyncio
async def test_model_precision_enum():
    """Test model precision enumeration"""
    assert ModelPrecision.FP32.value == "fp32"
    assert ModelPrecision.FP16.value == "fp16"
    assert ModelPrecision.BF16.value == "bf16"
    assert ModelPrecision.INT8.value == "int8"
    assert ModelPrecision.INT4.value == "int4"
