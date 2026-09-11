import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
Item {
    id:root; property var controller; property string currentTab:"overview"; signal navigateRequested(string mode); signal toastRequested(string message,string variant)
    Connections { target:root.controller; ignoreUnknownSignals:true; function onOperationFailed(message){root.toastRequested(message,"error")} function onOperationSucceeded(message){root.toastRequested(message,"success")} function onNavigationRequested(mode){root.navigateRequested(mode)} }
    ColumnLayout { anchors.fill:parent; spacing:Theme.spacing.md
        RowLayout { Layout.fillWidth:true
            ColumnLayout { Layout.fillWidth:true; Text { text:"Story Studio"; color:Theme.colors.textPrimary; font.pixelSize:Theme.type.titleLarge; font.weight:Theme.type.semibold }; Text { text:"Idea → Outline → Script → Voice → Scenes → Video • Offline deterministic planning"; color:Theme.colors.textMuted; font.pixelSize:Theme.type.caption } }
            Repeater { model:["overview","idea","outline","characters","script"]; AppButton { text:modelData.charAt(0).toUpperCase()+modelData.slice(1); compact:true; variant:root.currentTab===modelData?"secondary":"ghost"; onClicked:root.currentTab=modelData } }
        }
        StorySetup { Layout.fillWidth:true; Layout.fillHeight:true; visible:root.currentTab==="idea"; controller:root.controller }
        StoryOutline { Layout.fillWidth:true; Layout.fillHeight:true; visible:root.currentTab==="outline"; controller:root.controller }
        StoryCharacterPanel { Layout.fillWidth:true; Layout.fillHeight:true; visible:root.currentTab==="characters"; controller:root.controller }
        StoryScriptBuilder { Layout.fillWidth:true; Layout.fillHeight:true; visible:root.currentTab==="script"; controller:root.controller; onNavigateRequested:root.navigateRequested(mode) }
        StoryReadiness { Layout.fillWidth:true; Layout.fillHeight:true; visible:root.currentTab==="overview"; readiness:root.controller?root.controller.readiness:({}) }
        RowLayout { Layout.fillWidth:true; visible:root.currentTab==="overview"; SecondaryButton { text:"Idea"; onClicked:root.currentTab="idea" }; SecondaryButton { text:"Outline"; onClicked:root.currentTab="outline" }; SecondaryButton { text:"Script"; onClicked:root.navigateRequested("script") }; SecondaryButton { text:"Voice"; onClicked:root.navigateRequested("voices") }; SecondaryButton { text:"Scenes"; onClicked:root.navigateRequested("scenes") }; SecondaryButton { text:"Subtitles"; onClicked:root.navigateRequested("subtitles") }; SecondaryButton { text:"Timeline"; onClicked:root.navigateRequested("timeline") }; AppButton { text:"Export"; onClicked:root.navigateRequested("export") }; Item { Layout.fillWidth:true } }
    }
}
