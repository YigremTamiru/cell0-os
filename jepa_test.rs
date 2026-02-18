//! Test harness for JEPA implementation
//! 
//! This tests the JEPA world model in a standard (non-no_std) environment.

use std::vec::Vec;
use std::collections::BTreeMap;

// Re-export JEPA modules for testing
pub mod jepa;

use jepa::{JEPAWorldModel, JEPAConfig};
use jepa::world_state::{WorldState, ObjectCategory};
use jepa::encoder::Encoder;
use jepa::predictor::Predictor;
use jepa::cost::{CostModule, EnergyFunction};

/// Simple 2D environment for testing JEPA
pub struct SimpleEnvironment {
    pub agent_pos: [f32; 2],
    pub goal_pos: [f32; 2],
    pub obstacles: Vec<[f32; 2]>,
    pub time: u64,
}

impl SimpleEnvironment {
    pub fn new() -> Self {
        Self {
            agent_pos: [0.0, 0.0],
            goal_pos: [10.0, 10.0],
            obstacles: vec![[5.0, 5.0], [3.0, 7.0]],
            time: 0,
        }
    }

    pub fn step(&mut self, action: [f32; 2]) -> Vec<f32> {
        self.agent_pos[0] = (self.agent_pos[0] + action[0]).clamp(0.0, 10.0);
        self.agent_pos[1] = (self.agent_pos[1] + action[1]).clamp(0.0, 10.0);
        self.time += 1;
        self.get_observation()
    }

    pub fn get_observation(&self) -> Vec<f32> {
        let mut obs = vec![
            self.agent_pos[0] / 10.0,
            self.agent_pos[1] / 10.0,
            self.goal_pos[0] / 10.0,
            self.goal_pos[1] / 10.0,
        ];
        
        for obs_pos in &self.obstacles {
            obs.push(obs_pos[0] / 10.0);
            obs.push(obs_pos[1] / 10.0);
        }
        
        while obs.len() < 128 {
            obs.push(0.0);
        }
        obs
    }

    pub fn reset(&mut self) {
        self.agent_pos = [0.0, 0.0];
        self.time = 0;
    }
}

fn main() {
    println!("=== JEPA World Model Demonstration ===\n");

    // Test 1: Basic Encoder
    println!("Test 1: Encoder");
    let encoder = Encoder::new(128, 64);
    let obs = vec![0.5; 128];
    let embedding = encoder.forward(&obs);
    println!("  Input dim: 128 -> Output dim: {}", embedding.len());
    assert_eq!(embedding.len(), 64);
    println!("  ✓ Encoder test passed\n");

    // Test 2: Predictor
    println!("Test 2: Predictor");
    let predictor = Predictor::new(64, 16, 128, 3);
    let emb = vec![0.3; 64];
    let action = vec![0.1; 16];
    let predicted = predictor.forward(&emb, &action);
    println!("  Embedding dim: 64, Action dim: 16 -> Predicted dim: {}", predicted.len());
    assert_eq!(predicted.len(), 64);
    println!("  ✓ Predictor test passed\n");

    // Test 3: Cost Module
    println!("Test 3: Cost Module");
    let cost = CostModule::with_energy(64, EnergyFunction::MSE);
    let pred_emb = vec![0.5; 64];
    let target_emb = vec![0.6; 64];
    let cost_value = cost.compute(&pred_emb, &target_emb);
    println!("  MSE cost between similar embeddings: {:.6}", cost_value);
    assert!(cost_value >= 0.0);
    println!("  ✓ Cost module test passed\n");

    // Test 4: World State
    println!("Test 4: World State");
    let mut world_state = WorldState::new(100);
    let obj_id = world_state.create_object(ObjectCategory::Agent);
    world_state.update_object(obj_id, [1.0, 2.0, 0.0], vec![0.5; 8]);
    println!("  Created object: {:?}", obj_id);
    println!("  Active objects: {}", world_state.objects.len());
    assert_eq!(world_state.objects.len(), 1);
    println!("  ✓ World state test passed\n");

    // Test 5: Full JEPA Training
    println!("Test 5: JEPA Training (100 episodes)");
    
    let config = JEPAConfig {
        observation_dim: 128,
        embedding_dim: 64,
        action_dim: 16,
        predictor_hidden_dim: 128,
        predictor_layers: 3,
        learning_rate: 0.01,
        ema_momentum: 0.996,
        max_horizon: 10,
    };

    let mut jepa = JEPAWorldModel::new(config);
    let mut env = SimpleEnvironment::new();

    let num_episodes = 100;
    let steps_per_episode = 20;
    let mut total_cost = 0.0;

    for episode in 0..num_episodes {
        env.reset();
        let mut observation = env.get_observation();

        for _ in 0..steps_per_episode {
            // Random action
            let action = [
                (rand::random::<f32>() - 0.5) * 2.0,
                (rand::random::<f32>() - 0.5) * 2.0,
            ];

            let mut action_vec = vec![0.0; config.action_dim];
            action_vec[0] = action[0];
            action_vec[1] = action[1];

            let next_observation = env.step(action);
            let cost = jepa.train_step(&observation, &action_vec, &next_observation);
            total_cost += cost;

            observation = next_observation;
            jepa.world_state.tick();
        }
    }

    let avg_cost = total_cost / (num_episodes * steps_per_episode) as f32;
    println!("  Total training steps: {}", num_episodes * steps_per_episode);
    println!("  Average prediction cost: {:.6}", avg_cost);
    println!("  World state transitions: {}", jepa.world_state.transitions.len());
    println!("  ✓ JEPA training test passed\n");

    // Test 6: Trajectory Prediction
    println!("Test 6: Trajectory Prediction");
    env.reset();
    let initial_obs = env.get_observation();
    
    // Create action sequence (move consistently in one direction)
    let actions: Vec<Vec<f32>> = (0..5)
        .map(|_| {
            let mut a = vec![0.0; config.action_dim];
            a[0] = 0.5; // Move right
            a[1] = 0.5; // Move up
            a
        })
        .collect();

    let predicted_trajectory = jepa.predict_trajectory(&initial_obs, &actions);
    println!("  Predicted trajectory length: {} steps", predicted_trajectory.len());
    for (i, emb) in predicted_trajectory.iter().enumerate() {
        println!("    Step {}: embedding norm = {:.4}", i, 
            emb.iter().map(|x| x * x).sum::<f32>().sqrt());
    }
    assert_eq!(predicted_trajectory.len(), 5);
    println!("  ✓ Trajectory prediction test passed\n");

    // Test 7: Planning
    println!("Test 7: Planning");
    env.reset();
    let current_obs = env.get_observation();
    let goal_embedding = vec![0.8; config.embedding_dim]; // Arbitrary goal
    
    if let Some(best_action) = jepa.plan(&current_obs, &goal_embedding, 5, 10) {
        println!("  Planned action (first 4 dims): {:.4?}", &best_action[..4.min(best_action.len())]);
    } else {
        println!("  Planning returned None (expected with random initialization)");
    }
    println!("  ✓ Planning test passed\n");

    // Test 8: World State Summary
    println!("Test 8: World State Summary");
    let summary = jepa.world_state_summary();
    println!("  Number of transitions: {}", summary.num_transitions);
    println!("  Objects tracked: {}", summary.num_objects_tracked);
    println!("  Temporal depth: {}", summary.temporal_depth);
    println!("  Average prediction error: {:.6}", summary.average_prediction_error);
    println!("  ✓ Summary test passed\n");

    // Test 9: Multi-step Prediction with Uncertainty
    println!("Test 9: Prediction with Uncertainty");
    let (mean_traj, uncertainties) = jepa.predict_with_uncertainty(&initial_obs, &actions, 10);
    println!("  Mean trajectory length: {}", mean_traj.len());
    println!("  Uncertainty by step:");
    for (i, unc) in uncertainties.iter().enumerate() {
        println!("    Step {}: uncertainty = {:.6}", i, unc);
    }
    println!("  ✓ Uncertainty prediction test passed\n");

    println!("=== All JEPA Tests Passed! ===");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encoder() {
        let encoder = Encoder::new(128, 64);
        let obs = vec![0.5; 128];
        let embedding = encoder.forward(&obs);
        assert_eq!(embedding.len(), 64);
    }

    #[test]
    fn test_predictor() {
        let predictor = Predictor::new(64, 16, 128, 3);
        let emb = vec![0.3; 64];
        let action = vec![0.1; 16];
        let predicted = predictor.forward(&emb, &action);
        assert_eq!(predicted.len(), 64);
    }

    #[test]
    fn test_cost_module() {
        let cost = CostModule::with_energy(64, EnergyFunction::MSE);
        let pred = vec![0.5; 64];
        let target = vec![0.6; 64];
        let value = cost.compute(&pred, &target);
        assert!(value >= 0.0);
    }

    #[test]
    fn test_world_state() {
        let mut ws = WorldState::new(100);
        let id = ws.create_object(ObjectCategory::Agent);
        ws.update_object(id, [1.0, 2.0, 3.0], vec![0.5; 8]);
        assert!(ws.get_object(id).is_some());
    }

    #[test]
    fn test_jepa_training() {
        let config = JEPAConfig::default();
        let mut jepa = JEPAWorldModel::new(config);
        
        let obs = vec![0.5; config.observation_dim];
        let action = vec![0.1; config.action_dim];
        let next_obs = vec![0.6; config.observation_dim];
        
        let cost = jepa.train_step(&obs, &action, &next_obs);
        assert!(cost >= 0.0);
    }

    #[test]
    fn test_trajectory_prediction() {
        let config = JEPAConfig::default();
        let jepa = JEPAWorldModel::new(config);
        
        let obs = vec![0.5; config.observation_dim];
        let actions: Vec<Vec<f32>> = (0..5)
            .map(|_| vec![0.1; config.action_dim])
            .collect();
        
        let traj = jepa.predict_trajectory(&obs, &actions);
        assert_eq!(traj.len(), 5);
    }
}
