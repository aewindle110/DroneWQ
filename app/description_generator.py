import google.generativeai as genai
import json
import os
import time
from pathlib import Path

def generate_plot_descriptions(result_folder_path, api_key):
    """
    Generate accessible descriptions for all plots in the result folder.
    Saves descriptions to plot_descriptions.json
    """
    
    if not api_key or api_key.strip() == '':
        print("  No Gemini API key configured. Skipping description generation.")
        return {}
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')  # Updated model name
    except Exception as e:
        print(f"  Failed to initialize Gemini API: {e}")
        return {}
    
    # Define all possible plots
    plots = [
        {'key': 'rrs_plot', 'file': 'rrs_plot.png', 'type': 'Radiometry Spectra'},
        {'key': 'masked_rrs_plot', 'file': 'masked_rrs_plot.png', 'type': 'Masked Radiometry Spectra'},
        {'key': 'lt_plot', 'file': 'lt_plot.png', 'type': 'Total Radiance (Lt)'},
        {'key': 'ed_plot', 'file': 'ed_plot.png', 'type': 'Downwelling Irradiance (Ed)'},
        {'key': 'chl_hu_plot', 'file': 'chl_hu_plot.png', 'type': 'Chlorophyll-a (Hu Color Index)'},
        {'key': 'chl_ocx_plot', 'file': 'chl_ocx_plot.png', 'type': 'Chlorophyll-a (OCx Band Ratio)'},
        {'key': 'chl_hu_ocx_plot', 'file': 'chl_hu_ocx_plot.png', 'type': 'Chlorophyll-a (Blended)'},
        {'key': 'chl_gitelson_plot', 'file': 'chl_gitelson_plot.png', 'type': 'Chlorophyll-a (Gitelson)'},
        {'key': 'tsm_nechad_plot', 'file': 'tsm_nechad_plot.png', 'type': 'Total Suspended Matter'},
    ]
    
    descriptions = {}
    
    for plot in plots:
        image_path = os.path.join(result_folder_path, plot['file'])
        
        # Skip if file doesn't exist
        if not os.path.exists(image_path):
            continue
        
        print(f"Generating description for {plot['file']}...")
        
        try:
            # Read image
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Generate description
            prompt = f"""Analyze this {plot['type']} scientific plot and provide an accessible description.

                        Focus on:
                        1. Overall trends and patterns in the data
                        2. Key data points and their approximate values
                        3. Relationships between different lines or data series
                        4. Any notable features or anomalies

                        Do NOT rely on color descriptions. Instead use terms like "the thickest line", "the uppermost line", "the mean line", "most data series", etc.

                        Keep the description concise (2-3 sentences) but informative."""

            response = model.generate_content([
                prompt,
                {'mime_type': 'image/png', 'data': image_data}
            ])
            
            descriptions[plot['key']] = response.text.strip()
            print(f"✓ Generated description for {plot['file']}")
            
            # Rate limiting: wait between requests
            time.sleep(0.5)
            
        except Exception as e:
            print(f" Error generating description for {plot['file']}: {e}")
            descriptions[plot['key']] = "Description unavailable."
    
    # Save descriptions to JSON file
    if descriptions:
        output_path = os.path.join(result_folder_path, 'plot_descriptions.json')
        with open(output_path, 'w') as f:
            json.dump(descriptions, f, indent=2)
        print(f"\n Saved {len(descriptions)} descriptions to {output_path}")
    
    return descriptions