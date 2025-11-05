import re
import pandas as pd

def clean_research_interests(research_text):
    """
    Clean up research interests by removing repetitive boilerplate content
    and extracting only the meaningful research descriptions.
    """
    if not research_text or research_text == '':
        return ''
    
    # Common boilerplate text to remove
    boilerplate_patterns = [
        r'Research Areas[A-Za-z\s,&]+?Research Centers and Partnerships.*?Summer Research Program Participants',
        r'Research Areas[A-Za-z\s,&]+?Theory and Algorithms[A-Za-z\s,&]*',
        r'Architecture, Compilers and Parallel Computing.*?Theory and Algorithms',
        r'Research Centers and Partnerships.*?Summer Research Program Participants',
        r'Illinois-Insper Partnership.*?Summer Research Program Participants',
        r'Directed Reading Program.*?Summer Research Program Participants',
        r'Recent Courses Taught.*?Click for more',
    ]
    
    # Remove boilerplate
    cleaned = research_text
    for pattern in boilerplate_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.DOTALL)
    
    # Split by common separators and analyze each part
    parts = re.split(r'\s*\|\s*', cleaned)
    
    # Filter out parts that are just research area categories
    research_categories = {
        'architecture, compilers and parallel computing',
        'artificial intelligence',
        'bioinformatics and computational biology',
        'computers and education',
        'data and information systems',
        'interactive computing',
        'programming languages, formal methods and software engineering',
        'scientific computing',
        'security and privacy',
        'systems and networking',
        'theory and algorithms'
    }
    
    meaningful_parts = []
    for part in parts:
        part = part.strip()
        
        # Skip empty parts
        if not part:
            continue
            
        # Skip if it's just a research category
        if part.lower() in research_categories:
            continue
            
        # Skip if it's mostly research categories
        category_words = sum(1 for cat in research_categories if cat in part.lower())
        total_words = len(part.split())
        if category_words > total_words * 0.7:  # More than 70% category words
            continue
            
        # Skip very short parts that aren't meaningful
        if len(part) < 30:
            continue
            
        # Skip parts that are mostly awards/course info without research content
        if re.match(r'^(Recent Courses|Best Paper|Award|NSF|Teacher Ranked)', part):
            continue
            
        meaningful_parts.append(part)
    
    # Join meaningful parts
    result = ' | '.join(meaningful_parts)
    
    # Final cleanup
    result = re.sub(r'\s+', ' ', result)  # Normalize whitespace
    result = result[:1500]  # Limit length
    
    return result.strip()

def extract_specific_research_examples():
    """
    Show examples of good vs bad research interest extraction
    """
    
    # Sample from your data
    sample_data = [
        {
            'name': 'Faculty 1',
            'raw_research': 'Research AreasArchitecture, Compilers and Parallel ComputingArtificial IntelligenceBioinformatics and Computational BiologyComputers and EducationData and Information SystemsInteractive ComputingProgramming Languages, Formal Methods and Software EngineeringScientific ComputingSecurity and PrivacySystems and NetworkingTheory and AlgorithmsResearch Centers and PartnershipsIllinois-Insper PartnershipCollaborative Research ProjectsSummer Research ParticipantsSpeaker SeriesCorporate PartnersSummer ResearchUndergraduate Research OpportunitiesDirected Reading ProgramTrick or ResearchSummer Research ProgramSummer Research Program Participants | Social Sensing and Social Media AnalysisMachine Learning for IoT/CPSInternet of Things (IoT)Cyber-Physical Systems (CPS)Sensor Networks and CrowdsensingIntelligent Real-time Systems | Research AreasSystems and Networking'
        },
        {
            'name': 'Faculty 2', 
            'raw_research': 'Research AreasArchitecture, Compilers and Parallel ComputingArtificial IntelligenceBioinformatics and Computational BiologyComputers and EducationData and Information SystemsInteractive ComputingProgramming Languages, Formal Methods and Software EngineeringScientific ComputingSecurity and PrivacySystems and NetworkingTheory and AlgorithmsResearch Centers and PartnershipsIllinois-Insper PartnershipCollaborative Research ProjectsSummer Research ParticipantsSpeaker SeriesCorporate PartnersSummer ResearchUndergraduate Research OpportunitiesDirected Reading ProgramTrick or ResearchSummer Research ProgramSummer Research Program Participants | (1) Introduced a new computational approach to automatically extracting syntax of images, and using it for automated image understanding. We introduced automated ways of discovering, modeling, recognizing and explaining object categories occurring in arbitrary image sets without supervision and automatically organizing these categories into taxonomies. (2) Introduced a novel, Fourier based formulation for representation and synthesis of videos of dynamic textures. Conventionally, dynamic textures have been analyzed only in spatial domain. | Undergraduate student can participate in research projects in the areas of computer vision, pattern recognition, human computer interaction, novel cameras and image and video retrieval. | Computer Vision, Robotics, Image Processing, Sensors, Pattern Recognition, Virtual Environments, Intelligent Interfaces'
        }
    ]
    
    print("=== Research Interest Cleaning Examples ===\n")
    
    for i, faculty in enumerate(sample_data, 1):
        print(f"Faculty {i}: {faculty['name']}")
        print("Raw research interests (first 200 chars):")
        print(f"  {faculty['raw_research'][:200]}...\n")
        
        cleaned = clean_research_interests(faculty['raw_research'])
        print("Cleaned research interests:")
        print(f"  {cleaned}\n")
        print("-" * 80 + "\n")

def process_faculty_excel(input_file, output_file):
    """
    Process an Excel file to clean up research interests
    """
    try:
        # Read the Excel file
        df = pd.read_excel(input_file)
        
        if 'research_interests' not in df.columns:
            print("No 'research_interests' column found!")
            return
        
        print(f"Processing {len(df)} faculty members...")
        
        # Clean research interests
        df['research_interests_cleaned'] = df['research_interests'].apply(clean_research_interests)
        
        # Show statistics
        original_non_empty = sum(1 for x in df['research_interests'] if x and str(x).strip())
        cleaned_non_empty = sum(1 for x in df['research_interests_cleaned'] if x and str(x).strip())
        
        print(f"Original research interests: {original_non_empty}/{len(df)} faculty")
        print(f"Cleaned research interests: {cleaned_non_empty}/{len(df)} faculty")
        
        # Save cleaned version
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Faculty Directory', index=False)
            
            # Format columns
            worksheet = writer.sheets['Faculty Directory']
            
            # Set column widths
            column_widths = {
                'A': 25,  # name
                'B': 30,  # title  
                'C': 30,  # email
                'D': 15,  # phone
                'E': 15,  # office
                'F': 70,  # research_interests (original)
                'G': 70,  # research_interests_cleaned
            }
            
            for col, width in column_widths.items():
                worksheet.column_dimensions[col].width = width
        
        print(f"Saved cleaned data to {output_file}")
        
        # Show sample of cleaned data
        print("\nSample of cleaned research interests:")
        for i in range(min(3, len(df))):
            if df.iloc[i]['research_interests_cleaned']:
                print(f"\n{i+1}. {df.iloc[i]['name']}:")
                print(f"   {df.iloc[i]['research_interests_cleaned'][:200]}...")
                
    except Exception as e:
        print(f"Error processing file: {e}")

# Example usage
if __name__ == "__main__":
    print("Research Interest Cleaner")
    print("=" * 50)
    
    # Show examples
    extract_specific_research_examples()
    
    # If you have an Excel file to process:
    # process_faculty_excel('illinois_faculty_detailed.xlsx', 'illinois_faculty_cleaned.xlsx')
    
    print("To clean your Excel file, run:")
    print("process_faculty_excel('your_input_file.xlsx', 'cleaned_output.xlsx')")


process_faculty_excel('./illinois_faculty_detailed.xlsx', 'illinois_faculty_cleaned.xlsx')