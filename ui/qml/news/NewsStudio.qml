import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.ManualSpeech 1.0
import "../theme"
import "../components"
import "../speech"
import "visuals"
Item {
    id:root; property var controller; property var visualController; property string currentTab:"overview"; signal navigateRequested(string mode); signal toastRequested(string message,string variant)
    function stepForTab(){var m={overview:0,sources:0,claims:1,brief:2,script:2,speech:3,visuals:4};return m[currentTab]===undefined?0:m[currentTab]}
    Connections{target:root.controller;ignoreUnknownSignals:true;function onOperationFailed(message){root.toastRequested(message,"error")}function onOperationSucceeded(message){root.toastRequested(message,"success")}function onNavigationRequested(mode){root.navigateRequested(mode)}}
    Component.onCompleted: if(root.controller && root.controller.currentProjectId) ManualSpeech.setCurrentProject(root.controller.currentProjectId)
    ColumnLayout{anchors.fill:parent;spacing:Theme.spacing.md
        PageHeader{Layout.fillWidth:true;title:"News Studio";description:"Editorial workflow with evidence, review and clear publishing readiness.";actions:[SecondaryButton{text:"Open Mixer";compact:true;onClicked:root.navigateRequested("timeline")}]}
        WorkflowStepper{Layout.fillWidth:true;steps:["Sources","Claims","Script","Voice Script","Visuals","Export"];currentIndex:root.stepForTab();onStepRequested:function(i){if(i===0)root.currentTab="sources";else if(i===1)root.currentTab="claims";else if(i===2)root.currentTab="script";else if(i===3)root.currentTab="speech";else if(i===4)root.currentTab="visuals";else root.navigateRequested("export")}}
        SegmentTabs{items:["Overview","Sources","Claims","Brief","Script","Speech","Visuals"];currentIndex:["overview","sources","claims","brief","script","speech","visuals"].indexOf(root.currentTab);onActivated:function(i){root.currentTab=["overview","sources","claims","brief","script","speech","visuals"][i]}}
        NewsSetup{Layout.fillWidth:true;visible:root.currentTab==="overview";controller:root.controller}
        NewsReadiness{Layout.fillWidth:true;Layout.fillHeight:true;visible:root.currentTab==="overview";overview:root.controller?root.controller.overview:({})}
        NewsSources{Layout.fillWidth:true;Layout.fillHeight:true;visible:root.currentTab==="sources";controller:root.controller;onToastRequested:root.toastRequested(message,variant)}
        NewsClaims{Layout.fillWidth:true;Layout.fillHeight:true;visible:root.currentTab==="claims";controller:root.controller}
        NewsBrief{Layout.fillWidth:true;Layout.fillHeight:true;visible:root.currentTab==="brief";controller:root.controller}
        NewsScriptBuilder{Layout.fillWidth:true;Layout.fillHeight:true;visible:root.currentTab==="script";controller:root.controller;onNavigateRequested:root.navigateRequested(mode)}
        SpeechEditor{Layout.fillWidth:true;Layout.fillHeight:true;visible:root.currentTab==="speech";controller:ManualSpeech;projectId:root.controller?root.controller.currentProjectId:"";onToastRequested:root.toastRequested(message,variant)}
        NewsVisualStudio{Layout.fillWidth:true;Layout.fillHeight:true;visible:root.currentTab==="visuals";controller:root.visualController;onNavigateRequested:root.navigateRequested(mode);onToastRequested:root.toastRequested(message,variant)}
    }
}
