import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import os

# Configure the page
st.set_page_config(
    page_title="Hospital Capacity Planner",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1.5rem 0;
        background: linear-gradient(135deg, #1f77b4, #2ca02c);
        color: white;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    .critical { border-left-color: #d62728 !important; }
    .warning { border-left-color: #ff7f0e !important; }
    .good { border-left-color: #2ca02c !important; }
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }
    .csv-status-success {
        background: linear-gradient(135deg, #27ae60, #2ecc71);
        color: white;
        padding: 0.8rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        text-align: center;
        font-weight: 500;
        border-left: 4px solid #229954;
    }
    .csv-status-manual {
        background: linear-gradient(135deg, #f39c12, #f4d03f);
        color: white;
        padding: 0.8rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        text-align: center;
        font-weight: 500;
        border-left: 4px solid #e67e22;
    }
</style>
""", unsafe_allow_html=True)

# Professional title and description
st.markdown("""
<div class="main-header">
    <h1>🏥 Hospital Capacity Planning Dashboard</h1>
    <p>Strategic simulation tool for optimising staffing and reducing patient wait times</p>
    <p><em>Comprehensive analysis across 25 medical specialties</em></p>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# CSV AUTO-LOADING FUNCTIONS
# ============================================================================

@st.cache_data(ttl=60)  # Cache for 1 minute to allow fresh data loading
def load_csv_parameters(csv_path="hospital_parameters.csv"):
    """Load parameters from CSV file if it exists"""
    
    if not os.path.exists(csv_path):
        return None, None, "File not found"
    
    try:
        # Get file modification time
        file_stat = os.stat(csv_path)
        last_modified = datetime.fromtimestamp(file_stat.st_mtime)
        
        # Read CSV
        df = pd.read_csv(csv_path)
        
        # Column mapping for flexibility
        column_mapping = {
            'specialty': ['Specialty', 'specialty', 'SPECIALTY'],
            'doctors': ['Doctors', 'doctors', 'DOCTORS'],
            'non_doctors': ['Non_Doctors', 'non_doctors', 'NON_DOCTORS', 'Staff'],
            'doctor_rate': ['Doctor_Rate', 'doctor_rate', 'DOCTOR_RATE'],
            'non_doctor_rate': ['Non_Doctor_Rate', 'non_doctor_rate', 'NON_DOCTOR_RATE', 'Staff_Rate'],
            'initial_backlog': ['Initial_Backlog', 'initial_backlog', 'INITIAL_BACKLOG', 'Backlog'],
            'initial_wait': ['Initial_Wait', 'initial_wait', 'INITIAL_WAIT'],
            'daily_arrivals': ['Daily_Arrivals', 'daily_arrivals', 'DAILY_ARRIVALS', 'Arrivals']
        }
        
        # Find actual column names
        actual_columns = {}
        for key, possible_names in column_mapping.items():
            for name in possible_names:
                if name in df.columns:
                    actual_columns[key] = name
                    break
        
        # Check required columns
        required_keys = ['specialty', 'doctors', 'non_doctors', 'doctor_rate', 
                        'non_doctor_rate', 'initial_backlog', 'initial_wait', 'daily_arrivals']
        
        if not all(key in actual_columns for key in required_keys):
            missing = [key for key in required_keys if key not in actual_columns]
            return None, None, f"Missing columns: {missing}"
        
        # Convert to configuration dictionary
        config = {}
        for _, row in df.iterrows():
            try:
                specialty = str(row[actual_columns['specialty']]).strip()
                if specialty and specialty != 'nan':
                    config[specialty] = {
                        'doctors': int(float(row[actual_columns['doctors']])),
                        'non_doctors': int(float(row[actual_columns['non_doctors']])),
                        'doctor_rate': float(row[actual_columns['doctor_rate']]),
                        'non_doctor_rate': float(row[actual_columns['non_doctor_rate']]),
                        'initial_backlog': int(float(row[actual_columns['initial_backlog']])),
                        'initial_wait': int(float(row[actual_columns['initial_wait']])),
                        'daily_arrivals': int(float(row[actual_columns['daily_arrivals']]))
                    }
            except (ValueError, TypeError):
                continue
        
        if config:
            return config, last_modified, "success"
        else:
            return None, None, "No valid data found"
            
    except Exception as e:
        return None, None, f"Error reading CSV: {str(e)}"

# Core simulation functions
def calculate_metrics(specialty, doctors, non_doctors, doctor_rate, non_doctor_rate, 
                     initial_backlog, initial_wait, daily_arrivals, simulation_days):
    """
    Calculate comprehensive performance metrics for a hospital specialty.
    
    Returns dictionary with all key performance indicators including:
    - Capacity utilisation
    - Backlog projections
    - Wait time forecasts
    - Resource requirements
    """
    daily_capacity = doctors * doctor_rate + non_doctors * non_doctor_rate
    net_daily = daily_arrivals - daily_capacity
    
    # Project final state based on current trends
    final_backlog = max(0, initial_backlog + (net_daily * simulation_days))
    backlog_change = final_backlog - initial_backlog
    
    # Calculate wait time projections
    if final_backlog > 0 and initial_backlog > 0:
        final_wait = initial_wait * (final_backlog / initial_backlog)
    else:
        final_wait = 0
    wait_change = final_wait - initial_wait
    
    # Determine time to clear backlog
    if net_daily >= 0 or initial_backlog == 0:
        time_to_clear = "∞ (Impossible)" if initial_backlog > 0 else "N/A"
        months_to_clear = float('inf')
    else:
        days_to_clear = initial_backlog / abs(net_daily)
        months_to_clear = days_to_clear / 30
        time_to_clear = f"{months_to_clear:.0f} months"
    
    # Performance status classification
    if final_backlog < initial_backlog * 0.5:
        status = "🟢 Excellent"
        status_class = "good"
    elif final_backlog < initial_backlog:
        status = "🟡 Improving"
        status_class = "warning"
    elif final_backlog > initial_backlog * 1.5:
        status = "🔴 Critical"
        status_class = "critical"
    else:
        status = "🟠 Alert"
        status_class = "warning"
    
    return {
        'Specialty': specialty,
        'Doctors': doctors,
        'Non-Doctors': non_doctors,
        'Daily Capacity': daily_capacity,
        'Daily Arrivals': daily_arrivals,
        'Net Daily': net_daily,
        'Initial Backlog': initial_backlog,
        'Final Backlog': int(final_backlog),
        'Backlog Change': int(backlog_change),
        'Initial Wait (weeks)': initial_wait,
        'Final Wait (weeks)': int(round(final_wait, 0)),
        'Wait Change (weeks)': int(round(wait_change, 0)),
        'Time to Clear': time_to_clear,
        'Months to Clear': months_to_clear,
        'Utilisation (%)': int(round((daily_arrivals / daily_capacity) * 100, 0)),
        'Status': status,
        'Status Class': status_class
    }

def run_detailed_simulation(specialty_config, simulation_days):
    """
    Execute day-by-day simulation for detailed time series analysis.
    
    Tracks daily changes in:
    - Patient backlogs
    - Wait times
    - Treatment capacity
    - Resource utilisation
    """
    detailed_results = []
    
    for _, config in specialty_config.iterrows():
        specialty = config['Specialty']
        doctors = config['Doctors']
        non_doctors = config['Non-Doctors']
        doctor_rate = config['Doctor Rate']
        non_doctor_rate = config['Non-Doctor Rate']
        initial_backlog = config['Initial Backlog']
        initial_wait = config['Initial Wait']
        daily_arrivals = config['Daily Arrivals']
        
        daily_capacity = doctors * doctor_rate + non_doctors * non_doctor_rate
        current_backlog = initial_backlog
        
        for day in range(simulation_days):

            # Calculate dynamic wait time based on current backlog           
            if initial_backlog == 0 and current_backlog > 0:
                # perhaps assume current_wait = current_backlog / average_daily_capacity
                current_wait = current_backlog / daily_capacity   # in days or weeks
            elif current_backlog > 0 and initial_backlog > 0:
                current_wait = initial_wait * (current_backlog / initial_backlog)
            else:
                current_wait = 0


            # Process daily patient flow
            patients_treated = min(daily_capacity, current_backlog)
            current_backlog -= patients_treated
            current_backlog += daily_arrivals
            
            detailed_results.append({
                'Specialty': specialty,
                'Day': day + 1,
                'Backlog': int(current_backlog),
                'Wait Time (weeks)': int(round(current_wait, 0)),
                'Patients Treated': int(patients_treated)
            })
    
    return pd.DataFrame(detailed_results)

# Sidebar configuration
st.sidebar.header("⚙️ Simulation Parameters")

# ============================================================================
# CSV PARAMETER LOADING SECTION
# ============================================================================

# Try to load CSV parameters first
csv_config, csv_last_modified, csv_status = load_csv_parameters()
data_source_info = "Default Configuration"

# Display CSV status
if csv_status == "success":
    st.sidebar.markdown(f"""
    <div class="csv-status-success">
        ✅ <strong>Auto-loaded from CSV</strong><br>
        📄 hospital_parameters.csv<br>
        📅 {csv_last_modified.strftime('%b %d, %Y at %I:%M %p')}<br>
        🏥 {len(csv_config)} specialties loaded
    </div>
    """, unsafe_allow_html=True)
    data_source_info = f"Auto-loaded CSV ({csv_last_modified.strftime('%b %d, %Y at %I:%M %p')})"
    
    # Refresh button
    if st.sidebar.button("🔄 Refresh CSV", help="Reload hospital_parameters.csv"):
        st.cache_data.clear()
        st.rerun()
else:
    st.sidebar.info("📄 Place 'hospital_parameters.csv' in app directory for auto-loading")

# Manual CSV upload override
uploaded_file = st.sidebar.file_uploader(
    "📁 Manual CSV Upload", 
    type=['csv'],
    help="Override auto-loaded parameters with a different CSV file"
)

# Process manual upload
manual_config = None
if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        
        # Use same column mapping as auto-loading
        column_mapping = {
            'specialty': ['Specialty', 'specialty', 'SPECIALTY'],
            'doctors': ['Doctors', 'doctors', 'DOCTORS'],
            'non_doctors': ['Non_Doctors', 'non_doctors', 'NON_DOCTORS', 'Staff'],
            'doctor_rate': ['Doctor_Rate', 'doctor_rate', 'DOCTOR_RATE'],
            'non_doctor_rate': ['Non_Doctor_Rate', 'non_doctor_rate', 'NON_DOCTOR_RATE', 'Staff_Rate'],
            'initial_backlog': ['Initial_Backlog', 'initial_backlog', 'INITIAL_BACKLOG', 'Backlog'],
            'initial_wait': ['Initial_Wait', 'initial_wait', 'INITIAL_WAIT'],
            'daily_arrivals': ['Daily_Arrivals', 'daily_arrivals', 'DAILY_ARRIVALS', 'Arrivals']
        }
        
        actual_columns = {}
        for key, possible_names in column_mapping.items():
            for name in possible_names:
                if name in df.columns:
                    actual_columns[key] = name
                    break
        
        required_keys = ['specialty', 'doctors', 'non_doctors', 'doctor_rate', 
                        'non_doctor_rate', 'initial_backlog', 'initial_wait', 'daily_arrivals']
        
        if all(key in actual_columns for key in required_keys):
            manual_config = {}
            for _, row in df.iterrows():
                try:
                    specialty = str(row[actual_columns['specialty']]).strip()
                    if specialty and specialty != 'nan':
                        manual_config[specialty] = {
                            'doctors': int(float(row[actual_columns['doctors']])),
                            'non_doctors': int(float(row[actual_columns['non_doctors']])),
                            'doctor_rate': float(row[actual_columns['doctor_rate']]),
                            'non_doctor_rate': float(row[actual_columns['non_doctor_rate']]),
                            'initial_backlog': int(float(row[actual_columns['initial_backlog']])),
                            'initial_wait': int(float(row[actual_columns['initial_wait']])),
                            'daily_arrivals': int(float(row[actual_columns['daily_arrivals']]))
                        }
                except (ValueError, TypeError):
                    continue
            
            if manual_config:
                st.sidebar.markdown(f"""
                <div class="csv-status-manual">
                    📁 <strong>Manual Override Active</strong><br>
                    📄 {uploaded_file.name}<br>
                    🏥 {len(manual_config)} specialties loaded
                </div>
                """, unsafe_allow_html=True)
                data_source_info = f"Manual Upload: {uploaded_file.name}"
        else:
            st.sidebar.error("❌ Invalid CSV format - missing required columns")
            
    except Exception as e:
        st.sidebar.error(f"❌ Error reading file: {str(e)}")

# Global simulation settings
simulation_days = st.sidebar.slider(
    "Simulation Duration (days)", 
    min_value=30, 
    max_value=365, 
    value=180, 
    step=30,
    help="Select the time horison for capacity planning analysis"
)

st.sidebar.markdown("---")
st.sidebar.subheader("🏥 Specialty Configuration")

# Comprehensive hospital specialty configuration
# Organised by capacity deficit levels for realistic modeling
SPECIALTY_CONFIG = {
    # High-Demand Specialties (Capacity Constrained)
    'Dermatology': {
        'doctors': 6, 'non_doctors': 2, 'doctor_rate': 18, 'non_doctor_rate': 12,
        'initial_backlog': 1100, 'initial_wait': 65, 'daily_arrivals': 142,
    },
    'Anaesthesia': {
        'doctors': 8, 'non_doctors': 4, 'doctor_rate': 4, 'non_doctor_rate': 3,
        'initial_backlog': 950, 'initial_wait': 12, 'daily_arrivals': 51,
    },
    'Psychiatry': {
        'doctors': 6, 'non_doctors': 8, 'doctor_rate': 8, 'non_doctor_rate': 6,
        'initial_backlog': 1150, 'initial_wait': 85, 'daily_arrivals': 106,
    },
    'Emergency Medicine': {
        'doctors': 12, 'non_doctors': 15, 'doctor_rate': 25, 'non_doctor_rate': 15,
        'initial_backlog': 1200, 'initial_wait': 1, 'daily_arrivals': 530,
    },
    'Obs_Gyn': {
        'doctors': 6, 'non_doctors': 8, 'doctor_rate': 12, 'non_doctor_rate': 8,
        'initial_backlog': 930, 'initial_wait': 25, 'daily_arrivals': 148,
    },
    'Paediatrics': {
        'doctors': 8, 'non_doctors': 12, 'doctor_rate': 12, 'non_doctor_rate': 8,
        'initial_backlog': 960, 'initial_wait': 18, 'daily_arrivals': 200,
    },
    'Microbiology': {
        'doctors': 2, 'non_doctors': 8, 'doctor_rate': 20, 'non_doctor_rate': 25,
        'initial_backlog': 880, 'initial_wait': 3, 'daily_arrivals': 255,
    },
    'Plastic': {
        'doctors': 4, 'non_doctors': 3, 'doctor_rate': 8, 'non_doctor_rate': 6,
        'initial_backlog': 990, 'initial_wait': 65, 'daily_arrivals': 59,
    },
    
    # Balanced Specialties (Near Capacity Match)
    'Cardiothoracic Surgery': {
        'doctors': 2, 'non_doctors': 3, 'doctor_rate': 3, 'non_doctor_rate': 2,
        'initial_backlog': 900, 'initial_wait': 60, 'daily_arrivals': 12,
    },
    'Genetics': {
        'doctors': 1, 'non_doctors': 2, 'doctor_rate': 4, 'non_doctor_rate': 3,
        'initial_backlog': 870, 'initial_wait': 45, 'daily_arrivals': 11,
    },
    'Immunology': {
        'doctors': 2, 'non_doctors': 3, 'doctor_rate': 6, 'non_doctor_rate': 4,
        'initial_backlog': 880, 'initial_wait': 38, 'daily_arrivals': 23,
    },
    'Haematology': {
        'doctors': 3, 'non_doctors': 4, 'doctor_rate': 7, 'non_doctor_rate': 5,
        'initial_backlog': 860, 'initial_wait': 32, 'daily_arrivals': 41,
    },
    'Neurosurgery': {
        'doctors': 2, 'non_doctors': 4, 'doctor_rate': 2, 'non_doctor_rate': 1,
        'initial_backlog': 890, 'initial_wait': 75, 'daily_arrivals': 9,
    },
    'ENT': {
        'doctors': 3, 'non_doctors': 2, 'doctor_rate': 14, 'non_doctor_rate': 10,
        'initial_backlog': 950, 'initial_wait': 30, 'daily_arrivals': 61,
    },
    'Gastroenterology': {
        'doctors': 4, 'non_doctors': 3, 'doctor_rate': 7, 'non_doctor_rate': 5,
        'initial_backlog': 900, 'initial_wait': 45, 'daily_arrivals': 43,
    },
    'Orthopedics': {
        'doctors': 3, 'non_doctors': 2, 'doctor_rate': 12, 'non_doctor_rate': 8,
        'initial_backlog': 1200, 'initial_wait': 52, 'daily_arrivals': 53,
    },
    
    # High-Performing Specialties (Excess Capacity)
    'General Surgery': {
        'doctors': 8, 'non_doctors': 6, 'doctor_rate': 6, 'non_doctor_rate': 4,
        'initial_backlog': 1100, 'initial_wait': 48, 'daily_arrivals': 69,
    },
    'Genito-Urinary': {
        'doctors': 3, 'non_doctors': 2, 'doctor_rate': 10, 'non_doctor_rate': 7,
        'initial_backlog': 900, 'initial_wait': 28, 'daily_arrivals': 42,
    },
    'ICU': {
        'doctors': 10, 'non_doctors': 20, 'doctor_rate': 8, 'non_doctor_rate': 4,
        'initial_backlog': 870, 'initial_wait': 2, 'daily_arrivals': 155,
    },
    'Oncology': {
        'doctors': 5, 'non_doctors': 6, 'doctor_rate': 5, 'non_doctor_rate': 4,
        'initial_backlog': 920, 'initial_wait': 42, 'daily_arrivals': 45,
    },
    'Ophthalmology': {
        'doctors': 4, 'non_doctors': 3, 'doctor_rate': 16, 'non_doctor_rate': 12,
        'initial_backlog': 940, 'initial_wait': 55, 'daily_arrivals': 98,
    },
    'Paed Surg': {
        'doctors': 2, 'non_doctors': 3, 'doctor_rate': 4, 'non_doctor_rate': 3,
        'initial_backlog': 880, 'initial_wait': 45, 'daily_arrivals': 14,
    },
    'Public Health': {
        'doctors': 3, 'non_doctors': 6, 'doctor_rate': 15, 'non_doctor_rate': 12,
        'initial_backlog': 1010, 'initial_wait': 15, 'daily_arrivals': 112
    },
    'Cardiology': {
        'doctors': 5, 'non_doctors': 3, 'doctor_rate': 8, 'non_doctor_rate': 6,
        'initial_backlog': 900, 'initial_wait': 40, 'daily_arrivals': 55,
    },
    'Neurology': {
        'doctors': 2, 'non_doctors': 4, 'doctor_rate': 6, 'non_doctor_rate': 5,
        'initial_backlog': 950, 'initial_wait': 35, 'daily_arrivals': 30,
    }
}

# ============================================================================
# DETERMINE ACTIVE CONFIGURATION
# ============================================================================

# Priority: Manual upload > CSV auto-load > Default configuration
if manual_config:
    active_config = manual_config
    config_source_key = "manual"
elif csv_config:
    active_config = csv_config
    config_source_key = "csv"
else:
    active_config = SPECIALTY_CONFIG
    config_source_key = "default"

# User configuration interface
user_config = {}
specialty_count = len(active_config)

# Progress indicator with data source
st.sidebar.info(f"📊 Using: {data_source_info}")
st.sidebar.info(f"🏥 Configuring {specialty_count} hospital specialties")

# Clear session state when data source changes to force widget refresh
if 'last_config_source' not in st.session_state:
    st.session_state.last_config_source = config_source_key
elif st.session_state.last_config_source != config_source_key:
    # Data source changed, clear relevant session state keys
    keys_to_clear = [key for key in st.session_state.keys() if any(specialty in key for specialty in active_config.keys())]
    for key in keys_to_clear:
        del st.session_state[key]
    st.session_state.last_config_source = config_source_key

# Collapsible specialty configuration (widgets will show actual CSV values)
for specialty, defaults in active_config.items():
    with st.sidebar.expander(f"🏥 {specialty}", expanded=False):
        # Use unique keys that include config source to force refresh when source changes
        user_config[specialty] = {
            'doctors': st.number_input(
                "Doctors", 
                min_value=1, max_value=100, 
                value=defaults['doctors'], 
                key=f"{specialty}_docs_{config_source_key}",
                help="Number of qualified doctors"
            ),
            'non_doctors': st.number_input(
                "Non-Doctors", 
                min_value=1, max_value=100, 
                value=defaults['non_doctors'], 
                key=f"{specialty}_non_docs_{config_source_key}",
                help="Nurses, technicians, and support staff"
            ),
            'doctor_rate': defaults['doctor_rate'],
            'non_doctor_rate': defaults['non_doctor_rate'],
            'initial_backlog': st.number_input(
                "Initial Backlog", 
                min_value=0, max_value=50000, 
                value=defaults['initial_backlog'], 
                step=50, 
                key=f"{specialty}_backlog_{config_source_key}",
                help="Current number of patients waiting"
            ),
            'initial_wait': st.number_input(
                "Initial Wait (weeks)", 
                min_value=0, max_value=200, 
                value=defaults['initial_wait'], 
                key=f"{specialty}_wait_{config_source_key}",
                help="Current median wait time"
            ),
            'daily_arrivals': st.number_input(
                "Daily Arrivals", 
                min_value=1, max_value=2000, 
                value=defaults['daily_arrivals'], 
                key=f"{specialty}_arrivals_{config_source_key}",
                help="New patients per day"
            )
        }

# Simulation execution
if st.sidebar.button("🚀 Run Simulation", type="primary", use_container_width=True):
    with st.spinner("Running hospital capacity simulation..."):
        # Calculate performance metrics for all specialties
        results = []
        for specialty, config in user_config.items():
            result = calculate_metrics(
                specialty, 
                config['doctors'], 
                config['non_doctors'],
                config['doctor_rate'],
                config['non_doctor_rate'],
                config['initial_backlog'],
                config['initial_wait'],
                config['daily_arrivals'],
                simulation_days
            )
            results.append(result)
        
        results_df = pd.DataFrame(results)
        
        # Prepare detailed simulation data
        config_df = pd.DataFrame([
            {
                'Specialty': specialty,
                'Doctors': config['doctors'],
                'Non-Doctors': config['non_doctors'],
                'Doctor Rate': config['doctor_rate'],
                'Non-Doctor Rate': config['non_doctor_rate'],
                'Initial Backlog': config['initial_backlog'],
                'Initial Wait': config['initial_wait'],
                'Daily Arrivals': config['daily_arrivals']
            }
            for specialty, config in user_config.items()
        ])
        
        detailed_df = run_detailed_simulation(config_df, simulation_days)
        
        # Store results in session state
        st.session_state.results_df = results_df
        st.session_state.detailed_df = detailed_df
        st.session_state.data_source_info = data_source_info
        st.session_state.simulation_run = True
        
        st.success("✅ Simulation completed successfully!")

# Results display
if hasattr(st.session_state, 'simulation_run') and st.session_state.simulation_run:
    results_df = st.session_state.results_df
    detailed_df = st.session_state.detailed_df
    data_source_info = getattr(st.session_state, 'data_source_info', 'Unknown')
    
    # Latest Analysis Summary Box
    current_time = datetime.now()
    total_specialties = len(results_df)
    total_data_points = len(detailed_df)
    
    # Create professional summary box
    st.markdown("""
    <div style='background: linear-gradient(135deg, #2c3e50, #34495e); 
                padding: 1.5rem; 
                border-radius: 15px; 
                margin: 1rem 0 2rem 0;
                border-left: 5px solid #3498db;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);'>
        <h3 style='margin: 0 0 0.5rem 0; color: #ffffff; font-size: 1.2rem;'>
            📊 Latest Analysis
        </h3>
        <p style='margin: 0; color: #ecf0f1; font-size: 0.95rem; font-weight: 500;'>
            <strong>Completed:</strong> {completion_time}<br>
            <strong>Data Source:</strong> {data_source}<br>
            <strong>Duration:</strong> {duration} days • <strong>Specialties:</strong> {specialties} • <strong>Data Points:</strong> {data_points:,}
        </p>
    </div>
    """.format(
        completion_time=current_time.strftime("%B %d, %Y at %I:%M %p"),
        data_source=data_source_info,
        duration=simulation_days,
        specialties=total_specialties,
        data_points=total_data_points
    ), unsafe_allow_html=True)
    
    # Executive summary metrics
    st.header("📈 Executive Performance Dashboard")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        critical_count = len(results_df[results_df['Status'].str.contains('🔴')])
        st.metric(
            "Critical Specialties", 
            critical_count, 
            delta=f"of {len(results_df)} total",
            help="Departments requiring immediate intervention"
        )
    
    with col2:
        total_backlog_change = results_df['Backlog Change'].sum()
        st.metric(
            "Total Backlog Change", 
            f"{total_backlog_change:+,}",
            help="Net change in hospital-wide patient backlog"
        )
    
    with col3:
        avg_utilisation = int(results_df['Utilisation (%)'].mean())
        color = "normal" if 80 <= avg_utilisation <= 95 else "inverse"
        st.metric(
            "Average Utilisation", 
            f"{avg_utilisation}%",
            help="Hospital-wide capacity utilisation rate"
        )
    
    with col4:
        impossible_count = len(results_df[results_df['Time to Clear'].str.contains('∞')])
        st.metric(
            "Unsustainable Specialties", 
            impossible_count,
            delta=f"of {len(results_df)} total",
            help="Departments where demand exceeds capacity"
        )
    
    with col5:
        total_daily_capacity = results_df['Daily Capacity'].sum()
        total_daily_arrivals = results_df['Daily Arrivals'].sum()
        net_hospital_wide = total_daily_arrivals - total_daily_capacity
        st.metric(
            "Hospital Net Daily", 
            f"{net_hospital_wide:+,}",
            delta="patients/day",
            help="Daily surplus (+) or deficit (-) capacity"
        )
    
    # Strategic priority analysis
    st.header("🎯 Strategic Priority Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🚨 Immediate Action Required")
        worst_10 = results_df.nlargest(10, 'Backlog Change')[['Specialty', 'Backlog Change', 'Status']].copy()
        worst_10['Backlog Change'] = worst_10['Backlog Change'].apply(lambda x: f"{int(x):+,}")
        st.dataframe(worst_10, use_container_width=True, height=350)
    
    with col2:
        st.subheader("✅ High Performance Units")
        best_10 = results_df.nsmallest(10, 'Backlog Change')[['Specialty', 'Backlog Change', 'Status']].copy()
        best_10['Backlog Change'] = best_10['Backlog Change'].apply(lambda x: f"{int(x):+,}")
        st.dataframe(best_10, use_container_width=True, height=350)
    
    # Comprehensive performance visualisation
    st.header("📊 Performance Analytics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Backlog change analysis
        fig_backlog = px.bar(
            results_df, 
            x='Specialty', 
            y='Backlog Change',
            color='Backlog Change',
            color_continuous_scale=['green', 'red'],
            title="Backlog Change by Specialty",
            text='Backlog Change'
        )
        fig_backlog.update_traces(texttemplate='%{text:+,}', textposition='outside')
        fig_backlog.update_layout(showlegend=False, height=450)
        fig_backlog.update_xaxes(tickangle=45, title="Medical Specialty")
        fig_backlog.update_yaxes(title="Backlog Change (Patients)")
        st.plotly_chart(fig_backlog, use_container_width=True)
    
    with col2:
        # Wait time impact analysis
        fig_wait = px.bar(
            results_df,
            x='Specialty',
            y='Wait Change (weeks)',
            color='Wait Change (weeks)',
            color_continuous_scale=['green', 'red'],
            title="Wait Time Impact by Specialty",
            text='Wait Change (weeks)'
        )
        fig_wait.update_traces(texttemplate='%{text:+.0f}w', textposition='outside')
        fig_wait.update_layout(showlegend=False, height=450)
        fig_wait.update_xaxes(tickangle=45, title="Medical Specialty")
        fig_wait.update_yaxes(title="Wait Time Change (Weeks)")
        st.plotly_chart(fig_wait, use_container_width=True)
    
    with col3:
        # Capacity utilisation analysis
        fig_util = px.bar(
            results_df,
            x='Specialty',
            y='Utilisation (%)',
            color='Utilisation (%)',
            color_continuous_scale=['green', 'yellow', 'red'],
            title="Capacity Utilisation by Specialty",
            text='Utilisation (%)'
        )
        fig_util.update_traces(texttemplate='%{text:.0f}%', textposition='outside')
        fig_util.add_hline(
            y=100, 
            line_dash="dash", 
            line_color="red", 
            annotation_text="100% Capacity Threshold"
        )
        fig_util.update_layout(showlegend=False, height=450)
        fig_util.update_xaxes(tickangle=45, title="Medical Specialty")
        fig_util.update_yaxes(title="Utilisation Rate (%)")
        st.plotly_chart(fig_util, use_container_width=True)
    
    # Time series trend analysis
    st.header("📈 Trend Analysis")
    
    all_specialties = detailed_df['Specialty'].unique()
    
    selected_specialties = st.multiselect(
        "Select Specialties for Detailed Analysis",
        options=all_specialties,
        default=all_specialties[:6],
        help="Choose up to 8 specialties for optimal chart readability"
    )
    
    if selected_specialties:
        filtered_detailed = detailed_df[detailed_df['Specialty'].isin(selected_specialties)]
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Patient backlog trends
            fig_time_backlog = px.line(
                filtered_detailed,
                x='Day',
                y='Backlog',
                color='Specialty',
                title="Patient Backlog Trends Over Time",
                hover_data=['Patients Treated']
            )
            fig_time_backlog.update_layout(height=450)
            fig_time_backlog.update_xaxes(title="Simulation Day")
            fig_time_backlog.update_yaxes(title="Patient Backlog")
            st.plotly_chart(fig_time_backlog, use_container_width=True)
        
        with col2:
            # Wait time evolution
            fig_time_wait = px.line(
                filtered_detailed,
                x='Day',
                y='Wait Time (weeks)',
                color='Specialty',
                title="Wait Time Evolution Over Time"
            )
            fig_time_wait.update_layout(height=450)
            fig_time_wait.update_xaxes(title="Simulation Day")
            fig_time_wait.update_yaxes(title="Wait Time (Weeks)")
            st.plotly_chart(fig_time_wait, use_container_width=True)
    
    # Executive summary table
    st.header("📋 Executive Summary Report")
    
    # Prepare comprehensive executive table
    executive_df = results_df.copy()
    
    # Professional rate mappings
    rate_mappings = {
        'doctor_rates': {
            'Cardiology': '8/day', 'Orthopedics': '12/day', 'Neurology': '6/day',
            'Gastroenterology': '7/day', 'Dermatology': '18/day', 'Anaesthesia': '4/day',
            'Cardiothoracic Surgery': '3/day', 'Psychiatry': '8/day', 'Genetics': '4/day',
            'Immunology': '6/day', 'Emergency Medicine': '25/day', 'General Surgery': '6/day',
            'Genito-Urinary': '10/day', 'Haematology': '7/day', 'ICU': '8/day',
            'Microbiology': '20/day', 'Oncology': '5/day', 'Neurosurgery': '2/day',
            'Obs_Gyn': '12/day', 'Ophthalmology': '16/day', 'ENT': '14/day',
            'Paediatrics': '12/day', 'Paed Surg': '4/day', 'Plastic': '8/day',
            'Public Health': '15/day'
        },
        'non_doctor_rates': {
            'Cardiology': '6/day', 'Orthopedics': '8/day', 'Neurology': '5/day',
            'Gastroenterology': '5/day', 'Dermatology': '12/day', 'Anaesthesia': '3/day',
            'Cardiothoracic Surgery': '2/day', 'Psychiatry': '6/day', 'Genetics': '3/day',
            'Immunology': '4/day', 'Emergency Medicine': '15/day', 'General Surgery': '4/day',
            'Genito-Urinary': '7/day', 'Haematology': '5/day', 'ICU': '4/day',
            'Microbiology': '25/day', 'Oncology': '4/day', 'Neurosurgery': '1/day',
            'Obs_Gyn': '8/day', 'Ophthalmology': '12/day', 'ENT': '10/day',
            'Paediatrics': '8/day', 'Paed Surg': '3/day', 'Plastic': '6/day',
            'Public Health': '12/day'
        }
    }
    
    executive_df['Doctor Rate'] = executive_df['Specialty'].map(rate_mappings['doctor_rates'])
    executive_df['Non-Doctor Rate'] = executive_df['Specialty'].map(rate_mappings['non_doctor_rates'])
    
    # Format executive display table
    display_columns = [
        'Specialty', 'Doctor Rate', 'Non-Doctor Rate', 'Initial Backlog', 
        'Final Backlog', 'Backlog Change', 'Time to Clear', 'Initial Wait (weeks)', 
        'Final Wait (weeks)', 'Wait Change (weeks)', 'Daily Capacity', 
        'Daily Arrivals', 'Net Daily', 'Status'
    ]
    
    executive_display = executive_df[display_columns].copy()
    
    # Apply professional formatting
    def format_status(status):
        status_map = {
            '🟢': '🟢 Excellent',
            '🟡': '🟡 Improving',  
            '🔴': '🔴 Critical',
            '🟠': '🟠 Alert'
        }
        for key, value in status_map.items():
            if key in status:
                return value
        return status
    
    executive_display['System Status'] = executive_display['Status'].apply(format_status)
    executive_display = executive_display.drop('Status', axis=1)
    
    # Format numeric columns
    for col in ['Initial Backlog', 'Final Backlog', 'Initial Wait (weeks)', 
               'Final Wait (weeks)', 'Daily Capacity', 'Daily Arrivals']:
        if col in executive_display.columns:
            executive_display[col] = executive_display[col].astype(int)
    
    # Format change indicators with signs
    executive_display['Backlog Change'] = executive_display['Backlog Change'].apply(lambda x: f"{int(x):+d}")
    executive_display['Wait Change (weeks)'] = executive_display['Wait Change (weeks)'].apply(lambda x: f"{int(x):+d}")
    executive_display['Net Daily Change'] = executive_display['Net Daily'].apply(lambda x: f"{int(x):+d}")
    executive_display = executive_display.drop('Net Daily', axis=1)
    
    # Reorder for executive presentation
    final_columns = [
        'Specialty', 'Doctor Rate', 'Non-Doctor Rate', 'Initial Backlog', 
        'Final Backlog', 'Backlog Change', 'Time to Clear', 'Initial Wait (weeks)', 
        'Final Wait (weeks)', 'Wait Change (weeks)', 'Daily Capacity', 
        'Daily Arrivals', 'Net Daily Change', 'System Status'
    ]
    
    executive_display = executive_display[final_columns]
    
    # Apply conditional formatting for status
    def highlight_status(row):
        status = row['System Status']
        styles = [''] * len(row)
        
        if '🟢' in status:
            styles[-1] = 'background-color: #d4edda; color: #155724'
        elif '🟡' in status:
            styles[-1] = 'background-color: #fff3cd; color: #856404'
        elif '🔴' in status:
            styles[-1] = 'background-color: #f8d7da; color: #721c24'
        else:
            styles[-1] = 'background-color: #ffeaa7; color: #856404'
            
        return styles
    
    # Display professional executive table
    styled_executive = executive_display.style.apply(highlight_status, axis=1)
    st.dataframe(styled_executive, use_container_width=True, height=500)
    
    # Performance metrics summary
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        excellent_count = len(executive_display[executive_display['System Status'].str.contains('🟢')])
        st.metric("🟢 Excellent Performance", excellent_count)
    with col2:
        improving_count = len(executive_display[executive_display['System Status'].str.contains('🟡')])
        st.metric("🟡 Improving Performance", improving_count)
    with col3:
        alert_count = len(executive_display[executive_display['System Status'].str.contains('🟠')])
        st.metric("🟠 Alert/Monitoring", alert_count)
    with col4:
        critical_count = len(executive_display[executive_display['System Status'].str.contains('🔴')])
        st.metric("🔴 Critical Attention", critical_count)

    
    # Strategic recommendations
    st.header("💡 Strategic Recommendations")
    
    critical_specialties = results_df[results_df['Status'].str.contains('🔴')]['Specialty'].tolist()
    improving_specialties = results_df[results_df['Status'].str.contains('🟢')]['Specialty'].tolist()
    
    col1, col2 = st.columns(2)
    
    with col1:
        if critical_specialties:
            st.error("🚨 **Immediate Intervention Required**")
            for specialty in critical_specialties:
                row = results_df[results_df['Specialty'] == specialty].iloc[0]
                st.write(f"• **{specialty}**: {int(row['Backlog Change']):+,} patients, "
                        f"{int(row['Wait Change (weeks)']):+} weeks additional wait")
    
    with col2:
        if improving_specialties:
            st.success("✅ **High-Performing Units**")
            for specialty in improving_specialties:
                row = results_df[results_df['Specialty'] == specialty].iloc[0]
                st.write(f"• **{specialty}**: {int(row['Backlog Change']):+,} patients, "
                        f"{int(row['Wait Change (weeks)']):+} weeks wait change")
    
    # Action plan
    st.info("""
    **📋 Recommended Actions:**
    • **Resource Reallocation**: Redirect staff from high-performing to critical specialties
    • **Capacity Expansion**: Prioritise hiring for departments with >100% utilisation
    • **Process Optimisation**: Implement efficiency improvements in bottleneck areas
    • **Strategic Planning**: Develop long-term capacity plans for sustainable growth
    """)
    
    # Export functionality
    st.header("📤 Data Export")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Executive summary export
        csv_executive = executive_display.to_csv(index=False)
        st.download_button(
            label="📋 Download Executive Summary",
            data=csv_executive,
            file_name=f"hospital_executive_summary_{simulation_days}days.csv",
            mime="text/csv"
        )
    
    with col2:
        # Detailed data export
        csv_detailed = detailed_df.to_csv(index=False)
        st.download_button(
            label="📊 Download Detailed Data",
            data=csv_detailed,
            file_name=f"hospital_detailed_simulation_{simulation_days}days.csv",
            mime="text/csv"
        )

else:
    # Professional welcome interface
    st.info("👈 **Configure simulation parameters in the sidebar and click 'Run Simulation' to begin analysis**")
    
    st.markdown("""
    ## 🏥 Hospital Capacity Planning System
    
    ### **Strategic Decision Support Tool**
    
    This advanced simulation platform enables hospital administrators to:
    
    **📊 Comprehensive Analysis**
    • Model capacity across 25 medical specialties
    • Forecast patient wait times and backlog trends
    • Analyse resource utilisation and efficiency
    
    **🎯 Strategic Planning**
    • Test staffing scenarios before implementation
    • Identify critical capacity constraints
    • Optimise resource allocation decisions
    
    **📈 Performance Monitoring**
    • Track department-level performance metrics
    • Monitor system-wide capacity utilisation
    • Generate executive-ready reports
    
    ### **Enhanced Features**
    
    **🔄 Automated Parameter Loading**
    • Auto-loads from `hospital_parameters.csv` when available
    • Manual CSV upload for override/testing
    • Flexible column name handling
    • Real-time file modification tracking
    
    ### **Getting Started**
    
    1. **Place CSV File**: Put `hospital_parameters.csv` in app directory for auto-loading
    2. **Configure Parameters**: Adjust individual specialties if needed
    3. **Set Time Horizon**: Choose simulation duration (30-365 days)
    4. **Run Analysis**: Execute comprehensive capacity modeling
    5. **Review Results**: Analyse performance metrics and strategic recommendations
    6. **Export Data**: Download results for presentations and further analysis
    
    ### **Key Features**
    
    • **Auto-Refresh**: Seamless CSV parameter loading
    • **Real-time Simulation**: Dynamic modeling of patient flow and capacity
    • **Executive Dashboard**: Professional metrics and KPIs
    • **Strategic Analytics**: Priority analysis and performance benchmarking
    • **Trend Forecasting**: Time-series analysis of capacity trends
    • **Export Capabilities**: Professional reports and data downloads
    """)

# Professional footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem;'>
    <h4>🏥 Hospital Capacity Planning Dashboard</h4>
    <p><strong>Strategic Simulation Platform</strong> | Advanced Healthcare Analytics</p>
    <p><em>Optimise staffing • Reduce wait times • Improve patient outcomes</em></p>
</div>
""", unsafe_allow_html=True)