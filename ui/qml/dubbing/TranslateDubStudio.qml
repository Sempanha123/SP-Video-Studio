import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.ManualSpeech 1.0
import "../theme"
import "../components"
import "../speech"
Item {
    id:root;required property var controller;signal navigateRequested(string mode);property string tab:"overview"
    Connections{target:controller;function onNavigationRequested(mode){root.navigateRequested(mode)}}
    ColumnLayout{anchors.fill:parent;spacing:Theme.spacing.md
        PageHeader{Layout.fillWidth:true;title:"Translate & Dub";description:"Keep source, translation, voice and timing easy to compare.";actions:[StatusBadge{text:controller.readiness.state||"Not Ready";status:(controller.readiness.state||"").toLowerCase().indexOf("ready")>=0?"ready":"warning"},SecondaryButton{text:"Open Mixer";compact:true;onClicked:root.navigateRequested("timeline")}]}
        WorkflowStepper{Layout.fillWidth:true;steps:["Video","Transcript","Translation","Speech / Voice","Dub","Export"];currentIndex:0;onStepRequested:function(i){if(i===0)root.navigateRequested("media");else if(i===1)root.navigateRequested("transcript");else if(i===2)root.navigateRequested("translation");else if(i===3)speechDrawer.open();else if(i===5)root.navigateRequested("export")}}
        ScrollView{Layout.fillWidth:true;Layout.fillHeight:true;contentWidth:availableWidth
            ColumnLayout{width:parent.width;spacing:Theme.spacing.md
                DubSetup{Layout.fillWidth:true;controller:root.controller;onNavigateRequested:root.navigateRequested(mode)}
                RowLayout{Layout.fillWidth:true;spacing:Theme.spacing.md
                    DubTranscriptPanel{Layout.fillWidth:true;controller:root.controller;onNavigateRequested:root.navigateRequested(mode)}
                    DubTranslationPanel{Layout.fillWidth:true;controller:root.controller;onNavigateRequested:root.navigateRequested(mode)}
                }
                DubVoicePanel{Layout.fillWidth:true;controller:root.controller;onNavigateRequested:root.navigateRequested(mode)}
                SecondaryButton{text:"Open shared Speech / TTS Editor";onClicked:speechDrawer.open()}
                DubSegmentList{Layout.fillWidth:true;controller:root.controller}
                DubAudioMixPanel{Layout.fillWidth:true;controller:root.controller}
                DubPreview{Layout.fillWidth:true;controller:root.controller}
                DubReadiness{Layout.fillWidth:true;controller:root.controller;onNavigateRequested:root.navigateRequested(mode)}
            }
        }
    }
    Drawer{id:speechDrawer;edge:Qt.RightEdge;width:Math.min(root.width*.88,1120);height:root.height;modal:true
        SpeechEditor{anchors.fill:parent;anchors.margins:Theme.spacing.md;controller:ManualSpeech;projectId:controller.currentProjectId||""}
    }
}
