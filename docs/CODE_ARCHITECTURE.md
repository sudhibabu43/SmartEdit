# SmartEdit Code Architecture

```mermaid
graph TD
    User([User]) --> UI[Qt Desktop Interface]
    UI --> Core[SmartEdit Python Core]
    
    subgraph Python Application [smartedit-qt/src]
        Core --> MediaBin[Media Management]
        Core --> Timeline[Timeline Engine]
        Core --> Analysis[Video / Audio Analysis]
        Core --> SLM[SLM / AI Chat Assistant]
        
        SLM --> RoughCut[Rough-Cut Planner]
        RoughCut --> HitL[Human-in-the-Loop Review]
        HitL --> Timeline
    end
    
    subgraph External Libraries
        Analysis --> OpenCV[OpenCV]
        Analysis --> AudioLib[Librosa/Audio]
        Timeline --> LibSmartEdit[libsmartedit.dll / C++ Core]
        Timeline --> LibSmartEditAudio[libsmartedit-audio.dll / JUCE]
        LibSmartEdit --> FFmpeg[FFmpeg]
    end
    
    Timeline --> Rendering[Playback & Rendering]
```

## Description of Layers

- **Qt UI**: The presentation layer written in PyQt5.
- **SmartEdit Python Core**: The business logic orchestration layer.
- **Media / Timeline**: Manages media files, clips, tracking, and non-destructive properties.
- **Analysis**: Video and audio processing (Scene detection, shaky detection, silence detection). Uses OpenCV for visual analysis.
- **SLM & Rough-Cut Planner**: Interprets user commands into discrete editing `operations` and proposes `AIPlan` items to the user.
- **Human-in-the-Loop**: Presents proposed plans to the user before applying destructive timeline edits.
- **libsmartedit / FFmpeg**: The pre-compiled C++ multimedia backend (originally derived from OpenShot) that handles the actual frame rendering and video decoding via FFmpeg.
