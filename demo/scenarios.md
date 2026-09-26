# MilestoneAI demo scenarios

Both use **age 24 months**. In the app: sidebar → *Demo scenarios* → pick one → tick consent → **Check**.
The texts below are the same strings as `TA["demo_red"]` / `TA["demo_green"]` in `app.py`.

## 🔴 RED case (24 months)

What it describes: doesn't turn when called by name, doesn't point to show things, says only 3–4 single
words with no two-word phrases, lines up toy cars and cries if they're moved, doesn't react when his
sister cries.

> என் பையனுக்கு 2 வயசு. பேர் சொல்லிக் கூப்பிட்டா திரும்பிப் பாக்க மாட்டான். எதையும் விரல் நீட்டிக் காட்ட மாட்டான். 'அம்மா', 'தண்ணி', 'பால்' மாதிரி மூணு நாலு வார்த்தை மட்டும் தான் பேசுவான், ரெண்டு வார்த்தை சேர்த்துப் பேச மாட்டான். toy car எல்லாம் வரிசையா அடுக்கி வைப்பான், யாராவது நகர்த்துனா அழுவான். அவன் அக்கா அழுதா கூட கண்டுக்கவே மாட்டான்.

Expected: **RED**. Not responding to his name is a key item, and any key item answered "No" gives RED.
Lining up cars goes into the doctor note as a repetitive behaviour and is not scored.

## 🟢 GREEN case (24 months)

What it describes: says two-word phrases like "more milk", points at the dog to show his mother, looks
sad and pats his sister when she cries, turns when called by name, kicks a ball, eats with a spoon,
puts toy food on a toy plate.

It also covers eye contact, facial expressions, no lost skills, running, climbing stairs, pointing in a book and to body
parts, gestures, checking your face in a new place, and using both hands. Without those, the
coverage guard (every key item + 60% of items answered) would give **INCOMPLETE** instead of GREEN.

> என் பையனுக்கு 2 வயசு. 'more milk', 'அம்மா வா' மாதிரி ரெண்டு வார்த்தை சேர்த்துப் பேசுறான். நாய பாத்தா விரல் நீட்டி அவங்க அம்மாகிட்ட காட்டுறான். அக்கா அழுதா சோகமா பாத்துட்டு தட்டிக் குடுக்குறான். பேர் சொல்லிக் கூப்பிட்டா உடனே திரும்புறான். பந்த உதைக்கிறான், ஸ்பூன்ல தானே சாப்பிடுறான், toy plate-ல toy சாப்பாடு வச்சு விளையாடுறான். பேசும்போது என் கண்ணப் பாத்துப் பேசுறான். சந்தோஷம், கோபம், ஆச்சரியம் எல்லாம் அவன் முகத்துலயே தெரியும். முன்னாடி செஞ்ச எதையும் நிறுத்தல, புது வார்த்தைங்க கூடிட்டே தான் இருக்கு. நல்லா ஓடுறான், கைப்பிடிச்சு படி ஏறுறான். புக்ல 'நாய் எங்க?'ன்னு கேட்டா காட்டுறான், மூக்கு, கண்ணு எங்கன்னு கேட்டா தொட்டுக் காட்டுறான். flying kiss குடுப்பான், 'ஆமா'ன்னு தலை ஆட்டுவான். புது இடத்துக்குப் போனா என் முகத்தப் பாத்துட்டு தான் react பண்ணுவான். ஒரு கையில பொம்மைய புடிச்சுக்கிட்டு இன்னொரு கையால toy-ல button அமுக்கிப் பாப்பான்.

Expected: **GREEN**, provided the AI maps every key item and marks nothing "unclear".

## Short GREEN (shows the coverage guard)

Type only the first five sentences of the GREEN text. Expected: grey **INCOMPLETE** banner with the
missing key questions. Answer them and the result turns GREEN.
