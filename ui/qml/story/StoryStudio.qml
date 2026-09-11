import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.ManualSpeech 1.0
import "../theme"
import "../components"
import "../speech"
Item {
    id:root;property var controller;property string currentTab:"overview";signal navigateRequested(string mode);signal toastRequested(string message,string variant)
    Connections{target:root.controller;ignoreUnknownSignals:true;function onOperationFailed(message){root.toastRequested(message,"error")}function onOperationSucceeded(message){root.toastRequested(message,"success")}function onNavigationRequested(mode){root.navigateRequested(mode)}}
    ColumnLayout{anchors.fill:parent;spacing:Theme.spacing.md
        PageHeader{Layout.fillWidth:true;title:"Story Studio";description:"Shape an idea into a clear story, voice and scene plan.";actions:[SecondaryButton{text:"Open Mixer";compact:true;onClicked:root.navigateRequested("timeline")}]}
        WorkflowStepper{Layout.fillWidth:true;steps:["Idea","Outline","Script","Voice Script","Scenes","Export"];currentIndex:root.currentTab==="idea"?0:root.currentTab==="outline"?1:root.currentTab==="script"?2:root.currentTab==="speech"?3:0;onStepRequested:function(i){if(i===0)root.currentTab="idea";else if(i===1)root.currentTab="outline";else if(i===2)root.currentTab="script";else if(i===3)root.currentTab="speech";else if(i===4)root.navigateRequested("scenes");else root.navigateRequested("export")}}
        SegmentTabs{items:["Overview","Idea","Outline","Characters","Script","Speech"];currentIndex:["overview","idea","outline","characters","script","speech"].indexOf(root.currentTab);onActivated:function(i){root.currentTab=["overview","idea","outline","characters","script","speech"][i]}}
        StorySetup{Layout.fillWidth:true;Layout.fillHeight:true;visible:root.currentTab==="idea";controller:root.controller}
        StoryOutline{Layout.fillWidth:true;Layout.fillHeight:true;visible:root.currentTab==="outline";controller:root.controller}
        StoryCharacterPanel{Layout.fillWidth:true;Layout.fillHeight:true;visible:root.currentTab==="characters";controller:root.controller}
        StoryScriptBuilder{Layout.fillWidth:true;Layout.fillHeight:true;visible:root.currentTab==="script";controller:root.controller;onNavigateRequested:root.navigateRequested(mode)}
        SpeechEditor{Layout.fillWidth:true;Layout.fillHeight:true;visible:root.currentTab==="speech";controller:ManualSpeech;projectId:root.controller?root.controller.currentProjectId:"";onToastRequested:root.toastRequested(message,variant)}
        StoryReadiness{Layout.fillWidth:true;Layout.fillHeight:true;visible:root.currentTab==="overview";readiness:root.controller?root.controller.readiness:({})}
    }
}
