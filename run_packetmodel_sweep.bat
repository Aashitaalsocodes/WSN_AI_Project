@echo off
REM run_packetmodel_sweep.bat
REM Runs all remaining packet-model seed sweeps for TA-DT + 4 baselines.
REM Seed 42 is already done for all 5 protocols -- this covers TA-DT's
REM seed 42 (not yet run) plus every remaining seed for every protocol.
REM
REM Place this file in your WSN_AI_Project folder (same place as the
REM *_packetmodel.py files) and just double-click it, or run it from
REM Command Prompt: run_packetmodel_sweep.bat

echo ============================================
echo TA-DT (digital_twin_sim_multiseed_packetmodel.py)
echo ============================================
python digital_twin_sim_multiseed_packetmodel.py --seed 42
python digital_twin_sim_multiseed_packetmodel.py --seed 7
python digital_twin_sim_multiseed_packetmodel.py --seed 99
python digital_twin_sim_multiseed_packetmodel.py --seed 123
python digital_twin_sim_multiseed_packetmodel.py --seed 2024

echo ============================================
echo LEACH
echo ============================================
python baseline_leach_packetmodel.py --seed 7
python baseline_leach_packetmodel.py --seed 99
python baseline_leach_packetmodel.py --seed 123
python baseline_leach_packetmodel.py --seed 2024

echo ============================================
echo HEED
echo ============================================
python baseline_heed_packetmodel.py --seed 7
python baseline_heed_packetmodel.py --seed 99
python baseline_heed_packetmodel.py --seed 123
python baseline_heed_packetmodel.py --seed 2024

echo ============================================
echo TBR
echo ============================================
python baseline_tbr_packetmodel.py --seed 7
python baseline_tbr_packetmodel.py --seed 99
python baseline_tbr_packetmodel.py --seed 123
python baseline_tbr_packetmodel.py --seed 2024

echo ============================================
echo AI-SR
echo ============================================
python baseline_ai_sr_packetmodel.py --seed 7
python baseline_ai_sr_packetmodel.py --seed 99
python baseline_ai_sr_packetmodel.py --seed 123
python baseline_ai_sr_packetmodel.py --seed 2024

echo ============================================
echo ALL DONE. Check outputs\*_packetmodel_seed*.json
echo ============================================
pause