import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os

# 1. Load Production Data from CSV or Generate Forecast Data
# @st.cache_data
def load_or_generate_data():
    # Check if production_data.csv exists in the current directory
    if os.path.exists("production_data.csv"):
        return pd.read_csv("production_data.csv")

# Load data (either from CSV or newly generated)
demand_forecast = load_or_generate_data()

# 2. Define Manufacturing Steps and Capacities
manufacturing_steps = [
    'Deposition', 'Photolithography', 'Etching', 'Doping', 'CMP', 'Metrology'
]
default_capacities = {
    'Deposition': 23000, 'Photolithography': 22000, 'Etching': 22500,
    'Doping': 21500, 'CMP': 21000, 'Metrology': 24000
}

# 3. Streamlit Dashboard UI
st.title("Semiconductor Manufacturing Capacity Planning")
st.sidebar.header("Adjust Step Capacities")

# User inputs: Adjust capacities for each manufacturing step
step_capacities = {}
for step in manufacturing_steps:
    capacity = st.sidebar.number_input(
        f"{step} Capacity (units/day)", min_value=0, max_value=50000,
        value=default_capacities[step], step=500
    )
    step_capacities[step] = capacity

# 4. Simulate Production Through Each Step
def simulate_production(demand_forecast, step_capacities):
    df = demand_forecast.copy()
    df['processed_units'] = 0

    step_utilizations = {step: [] for step in manufacturing_steps}

    for i, step in enumerate(manufacturing_steps):
        capacity = step_capacities[step]

        if i == 0:
            df[step + '_processed'] = np.minimum(df['forecasted_demand'], capacity)
        else:
            previous_step = manufacturing_steps[i - 1]
            df[step + '_processed'] = np.minimum(df[previous_step + '_processed'], capacity)

        if i == len(manufacturing_steps) - 1:
            df['processed_units'] = df[step + '_processed']

        step_utilizations[step] = df[step + '_processed'] / capacity

    utilization_df = pd.DataFrame(step_utilizations)
    utilization_df['date'] = df['date']
    return df, utilization_df

# Run the simulation
production_df, utilization_df = simulate_production(demand_forecast, step_capacities)

# 5. Identify Bottlenecks
bottleneck_info = []
potential_bottleneck_info = []

for step in manufacturing_steps:
    actual_bottleneck_days = utilization_df[utilization_df[step] >= 1]['date']
    potential_bottleneck_days = utilization_df[(utilization_df[step] >= 0.85) & (utilization_df[step] < 1)]['date']

    if len(actual_bottleneck_days) > 0:
        bottleneck_info.append({
            'Step': f"<b style='color:red;'>{step}</b>",
            'Bottleneck Days': len(actual_bottleneck_days),
            'Percentage of Year': (len(actual_bottleneck_days) / len(utilization_df)) * 100
        })

    if len(potential_bottleneck_days) > 0:
        potential_bottleneck_info.append({
            'Step': step,
            'Potential Bottleneck Days': len(potential_bottleneck_days),
            'Percentage of Year': (len(potential_bottleneck_days) / len(utilization_df)) * 100
        })

# 6. Sidebar: Multi-Select Navigation
st.sidebar.markdown("## Navigate Sections")
sections = [
    "Utilization Rates for Each Manufacturing Step",
    "Bottleneck Analysis",
    "Strategic Insights",
    "Remaining Demand Over Time",
]

selected_sections = st.sidebar.multiselect("Select Sections to Display", sections, default=sections)

# 7. Display Selected Sections
if "Utilization Rates for Each Manufacturing Step" in selected_sections:
    st.subheader("Utilization Rates for Each Manufacturing Step")
    for step in manufacturing_steps:
        fig = px.line(
            utilization_df, x='date', y=step,
            title=f"{step} Utilization Rate",
            labels={'y': 'Utilization Rate', 'x': 'Date'}
        )
        fig.add_hline(y=1, line_dash="dash", line_color="red", annotation_text="100% Capacity")
        fig.add_hline(y=0.85, line_dash="dash", line_color="orange", annotation_text="85% Warning")
        st.plotly_chart(fig)

if "Bottleneck Analysis" in selected_sections:
    st.subheader("Bottleneck Analysis")
    if bottleneck_info:
        st.write("🚨 **Actual Bottlenecks Identified:**")
        bottleneck_df = pd.DataFrame(bottleneck_info)
        st.write(bottleneck_df.to_html(escape=False), unsafe_allow_html=True)
    else:
        st.write("✅ No actual bottlenecks detected.")

if "Strategic Insights" in selected_sections:
    st.subheader("Strategic Insights")
    if bottleneck_info or potential_bottleneck_info:
        st.write("**Recommendations:**")
        for info in bottleneck_info:
            st.markdown(f"- 🚨 Increase capacity in {info['Step']} to resolve the bottleneck.", unsafe_allow_html=True)
        for info in potential_bottleneck_info:
            st.write(f"- ⚠️ Monitor **{info['Step']}** closely to avoid future bottlenecks.")
    else:
        st.write("All steps have sufficient capacity.")

if "Remaining Demand Over Time" in selected_sections:
    st.subheader("Remaining Demand Over Time")
    fig2 = px.line(
        production_df, x='date', y=production_df['forecasted_demand'] - production_df['processed_units'],
        labels={'y': 'Unfulfilled Demand', 'x': 'Date'},
        title="Unfulfilled Demand Over Time"
    )
    st.plotly_chart(fig2)

# 8. Download Detailed Report
st.sidebar.subheader("📥 Download Detailed Report")
csv = production_df.to_csv(index=False).encode('utf-8')
st.sidebar.download_button(
    label="Download Production Data CSV",
    data=csv,
    file_name='production_data.csv',
    mime='text/csv'
)
