import asyncio
import os
import sys

sys.path.append("/app")
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from app.models import Chapter, Topic, Concept
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Pre-computed accurate curriculum mapping for Class 5
curriculum_data = {
    "Boundless Nature": [
        {"title": "Wonders of the Natural World", "concepts": [
            {"name": "Elements of Nature", "description": "Exploring plants, animals, and landscapes.", "learning_outcome": "Identify different elements of nature."},
            {"name": "Conservation", "description": "Understanding why we must protect nature.", "learning_outcome": "Explain the importance of nature conservation."}
        ]},
    ],
    "Friendship": [
        {"title": "Values of Friendship", "concepts": [
            {"name": "Trust and Honesty", "description": "The foundation of a good friendship.", "learning_outcome": "Understand the role of trust in relationships."},
            {"name": "Helping Others", "description": "Being there for friends in need.", "learning_outcome": "Demonstrate supportive behaviors towards peers."}
        ]}
    ],
    "Festivals - The Colours of Human Life": [
        {"title": "Cultural Significance", "concepts": [
            {"name": "Types of Festivals", "description": "National, religious, and harvest festivals.", "learning_outcome": "Categorize different types of festivals."},
            {"name": "Celebration Practices", "description": "How different communities celebrate.", "learning_outcome": "Describe varied cultural celebration practices."}
        ]}
    ],
    "Adventure": [
        {"title": "Exploring the Unknown", "concepts": [
            {"name": "Types of Adventures", "description": "Mountaineering, trekking, and exploring.", "learning_outcome": "Identify different adventurous activities."},
            {"name": "Safety and Preparation", "description": "What to pack and how to stay safe.", "learning_outcome": "List essential safety measures for adventures."}
        ]}
    ],
    "David and Goliath": [
        {"title": "Courage and Brains", "concepts": [
            {"name": "The Story of David", "description": "Analyzing the classic tale of the underdog.", "learning_outcome": "Summarize the story of David and Goliath."},
            {"name": "Moral Lesson", "description": "Understanding that intelligence overcomes size.", "learning_outcome": "Analyze the moral lesson of the story."}
        ]}
    ],
    "Our National Flag": [
        {"title": "Symbolism of the Flag", "concepts": [
            {"name": "The Tricolour", "description": "Meaning behind saffron, white, and green.", "learning_outcome": "Explain the significance of the flag's colors."},
            {"name": "Ashoka Chakra", "description": "The 24 spokes and their meaning.", "learning_outcome": "Describe the symbolism of the Ashoka Chakra."}
        ]}
    ],
    "Evaluation Activity": [
        {"title": "Semester Review", "concepts": [
            {"name": "Reading Comprehension", "description": "Reviewing stories and texts.", "learning_outcome": "Demonstrate comprehension of semester texts."},
            {"name": "Grammar and Vocabulary", "description": "Testing learned language rules.", "learning_outcome": "Apply grammar and vocabulary rules accurately."}
        ]}
    ],
    "The Brave Little Kite": [
        {"title": "Overcoming Fear", "concepts": [
            {"name": "Poem Analysis", "description": "Reading and understanding the poem.", "learning_outcome": "Summarize the theme of the poem."},
            {"name": "Theme of Courage", "description": "How the kite learned to fly.", "learning_outcome": "Explain how courage leads to success."}
        ]}
    ],
    "Srinivasa Ramanujan": [
        {"title": "The Mathematical Genius", "concepts": [
            {"name": "Early Life", "description": "Ramanujan's childhood and passion for numbers.", "learning_outcome": "Describe Ramanujan's early background."},
            {"name": "Contributions to Math", "description": "His discoveries in infinite series.", "learning_outcome": "Appreciate his contributions to mathematics."}
        ]}
    ],
    "A Shooting Test": [
        {"title": "Focus and Concentration", "concepts": [
            {"name": "The Mahabharata Story", "description": "Dronacharya's test for the Pandavas.", "learning_outcome": "Summarize the story of the shooting test."},
            {"name": "The Power of Focus", "description": "Why Arjuna saw only the bird's eye.", "learning_outcome": "Explain the importance of single-minded focus."}
        ]}
    ],
    "The Supremo": [
        {"title": "Leadership", "concepts": [
            {"name": "Qualities of a Leader", "description": "What makes someone the 'supremo' or best.", "learning_outcome": "Identify traits of a good leader."},
            {"name": "Responsibility", "description": "How leaders handle difficult situations.", "learning_outcome": "Discuss the responsibilities of leadership."}
        ]}
    ],
    "The King and the Tree Goddess": [
        {"title": "Nature and Wisdom", "concepts": [
            {"name": "The King's Desire", "description": "The king's wish to build a grand palace.", "learning_outcome": "Summarize the king's initial goal."},
            {"name": "The Goddess's Plea", "description": "Protecting the forest and its inhabitants.", "learning_outcome": "Analyze the environmental message of the story."}
        ]}
    ],
    "Truth is God": [
        {"title": "Honesty as a Virtue", "concepts": [
            {"name": "Gandhian Philosophy", "description": "Understanding Mahatma Gandhi's core belief.", "learning_outcome": "Explain the concept of 'Truth is God'."},
            {"name": "Practicing Honesty", "description": "Applying truthfulness in daily life.", "learning_outcome": "Reflect on personal instances of honesty."}
        ]}
    ],
    "Acknowledgement": [
        {"title": "Gratitude", "concepts": [
            {"name": "Expressing Thanks", "description": "How to formally thank contributors.", "learning_outcome": "Write a formal acknowledgement."},
            {"name": "Recognizing Help", "description": "Understanding the value of teamwork.", "learning_outcome": "Appreciate the efforts of others."}
        ]}
    ],
    "Super Senses": [
        {"title": "Animal Senses", "concepts": [
            {"name": "Incredible Hearing", "description": "How bats and dogs hear.", "learning_outcome": "Describe the hearing abilities of specific animals."},
            {"name": "Smell and Sight", "description": "How ants find food and eagles spot prey.", "learning_outcome": "Explain how animals use smell and sight."}
        ]}
    ],
    "A Snake and Snake Charmer": [
        {"title": "Traditional Livelihoods", "concepts": [
            {"name": "The Kalbeliya Tribe", "description": "Life and culture of snake charmers.", "learning_outcome": "Describe the lifestyle of the Kalbeliya people."},
            {"name": "Wildlife Protection Act", "description": "Why keeping snakes is now illegal.", "learning_outcome": "Explain the purpose of wildlife protection laws."}
        ]}
    ],
    "From Tasting to Digesting": [
        {"title": "The Human Digestive System", "concepts": [
            {"name": "Taste Buds", "description": "How the tongue identifies different tastes.", "learning_outcome": "Identify the function of taste buds."},
            {"name": "Journey of Food", "description": "From the mouth to the stomach and intestines.", "learning_outcome": "Trace the path of food through the digestive system."}
        ]}
    ],
    "Mangoes Round the Year": [
        {"title": "Food Preservation", "concepts": [
            {"name": "Spoilage of Food", "description": "Why food goes bad due to moisture and microbes.", "learning_outcome": "Identify the causes of food spoilage."},
            {"name": "Preservation Techniques", "description": "Making pickles, aam papad, and drying.", "learning_outcome": "Describe different methods to preserve food."}
        ]}
    ],
    "Seed, Seed, Seed": [
        {"title": "Plant Reproduction", "concepts": [
            {"name": "Seed Germination", "description": "Conditions required for a seed to sprout.", "learning_outcome": "List the conditions necessary for germination."},
            {"name": "Seed Dispersal", "description": "How seeds travel via wind, water, and animals.", "learning_outcome": "Explain various methods of seed dispersal."}
        ]}
    ],
    "Water is Life": [
        {"title": "Water Conservation", "concepts": [
            {"name": "Sources of Water", "description": "Lakes, rivers, wells, and rain.", "learning_outcome": "Identify natural sources of fresh water."},
            {"name": "Rainwater Harvesting", "description": "Collecting and storing rainwater.", "learning_outcome": "Explain the process and benefits of rainwater harvesting."}
        ]}
    ],
    "Experiments with Water": [
        {"title": "Properties of Water", "concepts": [
            {"name": "Floating and Sinking", "description": "Understanding density and buoyancy.", "learning_outcome": "Predict which objects will float or sink."},
            {"name": "Solubility", "description": "What dissolves in water and what doesn't.", "learning_outcome": "Differentiate between soluble and insoluble substances."}
        ]}
    ],
    "Mosquitoes: Diseases and Treatment": [
        {"title": "Vector-Borne Diseases", "concepts": [
            {"name": "Malaria and Dengue", "description": "Diseases spread by mosquitoes.", "learning_outcome": "Identify diseases transmitted by mosquitoes."},
            {"name": "Prevention", "description": "Using nets, repellents, and clearing stagnant water.", "learning_outcome": "List methods to prevent mosquito breeding."}
        ]}
    ],
    "Climbing High": [
        {"title": "Mountaineering", "concepts": [
            {"name": "Equipment and Preparation", "description": "Tools needed to climb mountains safely.", "learning_outcome": "List essential mountaineering equipment."},
            {"name": "Physical and Mental Strength", "description": "The challenges faced during expeditions.", "learning_outcome": "Discuss the physical demands of mountain climbing."}
        ]}
    ],
    "Story of Walls": [
        {"title": "Historical Monuments", "concepts": [
            {"name": "Fort Architecture", "description": "Bastions, thick walls, and defense mechanisms.", "learning_outcome": "Describe the architectural features of ancient forts."},
            {"name": "Preserving Heritage", "description": "Why we must protect historical sites.", "learning_outcome": "Explain the importance of heritage conservation."}
        ]}
    ],
    "Sunita in Space": [
        {"title": "Space Exploration", "concepts": [
            {"name": "Zero Gravity", "description": "How things behave in a spaceship.", "learning_outcome": "Explain the concept of weightlessness in space."},
            {"name": "The Earth from Space", "description": "Understanding the shape and borders of Earth.", "learning_outcome": "Describe how Earth looks from a spacecraft."}
        ]}
    ],
    "What if this will be Finished?": [
        {"title": "Fossil Fuels", "concepts": [
            {"name": "Non-Renewable Resources", "description": "Coal, petroleum, and natural gas.", "learning_outcome": "Define non-renewable energy sources."},
            {"name": "Saving Energy", "description": "Alternative energy sources and conservation.", "learning_outcome": "Suggest ways to conserve petroleum."}
        ]}
    ],
    "Shelter High": [
        {"title": "Life in High Altitudes", "concepts": [
            {"name": "Changpa Tribe", "description": "Nomadic life in the cold deserts of Ladakh.", "learning_outcome": "Describe the lifestyle of the Changpa tribe."},
            {"name": "Pashmina Wool", "description": "Rearing goats for high-quality wool.", "learning_outcome": "Explain the source and value of Pashmina."}
        ]}
    ],
    "When the Earth Shook": [
        {"title": "Natural Disasters", "concepts": [
            {"name": "Earthquakes", "description": "What causes tremors and how to stay safe.", "learning_outcome": "List safety protocols during an earthquake."},
            {"name": "Relief and Rehabilitation", "description": "Helping communities rebuild after a disaster.", "learning_outcome": "Discuss the role of relief agencies."}
        ]}
    ],
    "Cold or Hot?": [
        {"title": "Air and Breathing", "concepts": [
            {"name": "Blowing Air", "description": "How our breath can both warm hands and cool tea.", "learning_outcome": "Explain how blowing air affects temperature."},
            {"name": "The Stethoscope", "description": "Listening to heartbeats and breathing.", "learning_outcome": "Describe the function of a stethoscope."}
        ]}
    ],
    "Cleaning is our job": [
        {"title": "Dignity of Labour", "concepts": [
            {"name": "Respecting All Work", "description": "No job is small or inferior.", "learning_outcome": "Explain the concept of dignity of labor."},
            {"name": "Gandhiji's Teachings", "description": "Mahatma Gandhi's views on cleanliness and equality.", "learning_outcome": "Summarize Gandhiji's approach to community cleaning."}
        ]}
    ],
    "Across the Wall": [
        {"title": "Gender Equality in Sports", "concepts": [
            {"name": "Overcoming Stereotypes", "description": "Girls playing sports and breaking barriers.", "learning_outcome": "Discuss the importance of gender equality in sports."},
            {"name": "Team Spirit", "description": "Working together regardless of background.", "learning_outcome": "Define team spirit and cooperation."}
        ]}
    ],
    "Where do we go now?": [
        {"title": "Displacement and Migration", "concepts": [
            {"name": "Building Dams", "description": "Why villages are submerged for large projects.", "learning_outcome": "Explain the reasons behind building large dams."},
            {"name": "Life of Migrants", "description": "Challenges faced when moving to a new city.", "learning_outcome": "Describe the difficulties faced by displaced communities."}
        ]}
    ],
    "A Seed Tells Farmer's Story": [
        {"title": "Farming Changes over Time", "concepts": [
            {"name": "Traditional vs Modern Farming", "description": "From natural manure to chemical fertilizers.", "learning_outcome": "Compare traditional and modern farming methods."},
            {"name": "Impact on Soil", "description": "How over-farming affects soil fertility.", "learning_outcome": "Explain the long-term effects of chemical fertilizers."}
        ]}
    ],
    "Whose Forests?": [
        {"title": "Rights of Forest Dwellers", "concepts": [
            {"name": "Adivasi Life", "description": "Depending on the forest for livelihood.", "learning_outcome": "Describe the relationship between Adivasis and forests."},
            {"name": "Right to Forest Act", "description": "Laws protecting indigenous tribes.", "learning_outcome": "Explain the purpose of the Right to Forest Act."}
        ]}
    ],
    "Like Father, Like Daughter": [
        {"title": "Heredity and Traits", "concepts": [
            {"name": "Inherited Characteristics", "description": "Traits we get from our parents.", "learning_outcome": "Identify physical traits inherited from family."},
            {"name": "Acquired Skills", "description": "Things we learn from our environment.", "learning_outcome": "Differentiate between inherited traits and acquired skills."}
        ]}
    ],
    "On the Move Again": [
        {"title": "Seasonal Migration", "concepts": [
            {"name": "Sugarcane Farming", "description": "Moving for agricultural work during harvest.", "learning_outcome": "Explain why families migrate seasonally for work."},
            {"name": "Impact on Education", "description": "How migration affects children's schooling.", "learning_outcome": "Discuss the challenges migrant children face in education."}
        ]}
    ],
    "We are Gujarati...": [
        {"title": "Regional Identity", "concepts": [
            {"name": "Culture and Language", "description": "The unique traditions of Gujarat.", "learning_outcome": "Describe key elements of Gujarati culture."},
            {"name": "Geography of Gujarat", "description": "Important landmarks and physical features.", "learning_outcome": "Identify major geographical features of Gujarat."}
        ]}
    ]
}

from sqlalchemy import text
from app.models import Chapter, Topic, Concept, LearningOutcome

async def main():
    async with async_session() as session:
        # Get all chapters with 0 topics
        result = await session.execute(text("""
            SELECT c.id, c.title_en
            FROM chapters c 
            WHERE NOT EXISTS (SELECT 1 FROM topics t WHERE t.chapter_id = c.id)
        """))
        chapters = result.fetchall()
        
        print(f"Injecting pre-computed topics for {len(chapters)} chapters...")
        
        for ch_id, ch_title in chapters:
            if ch_title in curriculum_data:
                topics = curriculum_data[ch_title]
                for seq, t_data in enumerate(topics, 1):
                    topic = Topic(chapter_id=ch_id, sequence=seq, title_en=t_data["title"])
                    session.add(topic)
                    await session.flush()
                    
                    for c_seq, c_data in enumerate(t_data["concepts"], 1):
                        concept = Concept(
                            topic_id=topic.id,
                            name_en=c_data["name"],
                            description=c_data["description"]
                        )
                        session.add(concept)
                        await session.flush()
                        
                        outcome = LearningOutcome(
                            concept_id=concept.id,
                            description_en=c_data["learning_outcome"]
                        )
                        session.add(outcome)
                        
                print(f"Added topics for {ch_title}")
        
        await session.commit()
        print("Done injecting all concepts!")

if __name__ == "__main__":
    asyncio.run(main())
