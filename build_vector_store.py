import pandas as pd
import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
import os
from typing import List, Dict, Any
import json
from chromadb.config import Settings

class PropertyVectorStore:
    def __init__(self, persist_directory: str = "property_vector_store"):
        """
        Initialize the property vector store.
        
        Args:
            persist_directory: Directory to persist the vector store
        """
        self.persist_directory = persist_directory
        
        # Initialize the sentence transformer model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize ChromaDB client with telemetry disabled
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Create or get the collection
        self.collection = self.client.get_or_create_collection(
            name="properties",
            embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
        )
        
    def _prepare_property_text(self, row: pd.Series) -> str:
        """
        Prepare the text representation of a property for embedding.
        
        Args:
            row: A pandas Series containing property data
            
        Returns:
            str: Formatted text representation of the property
        """
        text = f"""
        Property: {row['property_name']}
        Location: {row['location']}
        Country: {row['country']}
        Type: {row['property_type_1']}
        Bedrooms: {row['bedrooms']}
        Price: {row['starting_price']}
        Description: {row['property_description']}
        """
        
        # Add amenities if available
        if 'amenities' in row and pd.notna(row['amenities']):
            text += f"\nAmenities: {row['amenities']}"
            
        return text
    
    def _prepare_metadata(self, row: pd.Series) -> Dict[str, Any]:
        """
        Prepare metadata for a property.
        
        Args:
            row: A pandas Series containing property data
            
        Returns:
            Dict[str, Any]: Property metadata
        """
        metadata = {
            "property_name": row["property_name"],
            "location": row["location"],
            "property_type": row["property_type_1"],
            "bedrooms": row["bedrooms"],
            "price": row["starting_price"],
            "description": row["property_description"],
            "hero_image_link": row["hero_image_link"],
            "compressed_hero_image_link": row["compressed_hero_image_link"],
            "brochure": row["brochure"],
            "floor_plans": row["floor_plans"],
            "country": row["country"]
        }
        
        # Add amenities if available
        if 'amenities' in row and pd.notna(row['amenities']):
            metadata["amenities"] = row["amenities"]
            
        return metadata
    
    def build_vector_store(self):
        """
        Build the vector store from all three CSV files.
        """
        # Read all CSV files
        properties_df = pd.read_csv("property_details_rows.csv")
        locations_df = pd.read_csv("property_details_locations_rows.csv")
        amenities_df = pd.read_csv("property_details_amenities_rows.csv")
        
        # Merge the dataframes - use properties as base and left join others
        # This ensures we keep all properties even if they don't have location/amenities data
        merged_df = properties_df.merge(
            locations_df,
            on="id",
            how="left",
            suffixes=('', '_location')
        ).merge(
            amenities_df,
            on="id",
            how="left",
            suffixes=('', '_amenities')
        )
        
        print(f"Total properties in main CSV: {len(properties_df)}")
        print(f"Properties with location data: {len(locations_df)}")
        print(f"Properties with amenities data: {len(amenities_df)}")
        print(f"Properties after merge: {len(merged_df)}")
        
        # Prepare data for ChromaDB
        documents = []
        metadatas = []
        ids = []
        
        for _, row in merged_df.iterrows():
            # Prepare the text representation
            text = self._prepare_property_text(row)
            documents.append(text)
            
            # Prepare metadata
            metadata = self._prepare_metadata(row)
            metadatas.append(metadata)
            
            # Use the property ID as the document ID
            ids.append(str(row["id"]))
        
        # Add documents to the collection
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        # print(f"Successfully added {len(documents)} properties to the vector store")
    
    def search_by_country(self, country: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for properties in a specific country.
        
        Args:
            country: Country name to search for
            n_results: Number of results to return
            
        Returns:
            List[Dict[str, Any]]: List of matching properties with their metadata
        """
        # Get all properties and filter by country
        all_results = self.collection.get()
        
        # Filter by country
        georgia_properties = []
        for i, metadata in enumerate(all_results['metadatas']):
            if metadata.get('country', '').lower() == country.lower():
                georgia_properties.append({
                    "id": all_results["ids"][i],
                    "metadata": metadata,
                    "distance": 0.0  # No distance calculation for country filter
                })
        
        # Return top n_results
        return georgia_properties[:n_results]

    def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for properties similar to the query.
        
        Args:
            query: Search query
            n_results: Number of results to return
            
        Returns:
            List[Dict[str, Any]]: List of matching properties with their metadata
        """
        # Check if query is asking for a specific country
        query_lower = query.lower()
        if any(country in query_lower for country in ['georgia', 'batumi', 'tbilisi']):
            return self.search_by_country('Georgia', n_results)
        elif any(country in query_lower for country in ['uae', 'dubai', 'abu dhabi', 'sharjah', 'ras al khaimah']):
            return self.search_by_country('United Arab Emirates', n_results)
        
        # Regular semantic search
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        # Format the results
        formatted_results = []
        for i in range(len(results["ids"][0])):
            formatted_results.append({
                "id": results["ids"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i] if "distances" in results else None
            })
        
        return formatted_results

def main():
    # Initialize the vector store
    vector_store = PropertyVectorStore()
    
    # Build the vector store
    vector_store.build_vector_store()
    
    # Example search
    results = vector_store.search("Find properties near Dubai Mall")
    print("\nSearch Results:")
    for result in results:
        print(f"\nProperty: {result['metadata']['property_name']}")
        print(f"Location: {result['metadata']['location']}")
        if 'amenities' in result['metadata']:
            print(f"Amenities: {result['metadata']['amenities']}")
        print(f"Distance Score: {result['distance']}")

if __name__ == "__main__":
    main()
