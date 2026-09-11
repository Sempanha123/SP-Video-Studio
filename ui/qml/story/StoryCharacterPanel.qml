import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
Item {
    id: root; property var controller
    ColumnLayout { anchors.fill: parent; spacing: Theme.spacing.md
        SectionHeader { title: "Characters & Voices"; subtitle: "Production metadata only. Voice profiles stay managed by Voice Studio." }
        RowLayout { Layout.fillWidth: true; AppTextField { id:nameField; Layout.fillWidth:true; placeholderText:"Character name" }; AppComboBox { id:roleBox; model:["Narrator","Main Character","Supporting Character","Expert","Host","Other"] }; AppButton { text:"Add"; onClicked: if(root.controller && nameField.text) { root.controller.addCharacter(nameField.text,roleBox.currentText.toLowerCase().replace(/ /g,"_"),""); nameField.text="" } } }
        ScrollView { Layout.fillWidth:true; Layout.fillHeight:true; Column { width:parent.width; spacing:Theme.spacing.sm; Repeater { model:root.controller?root.controller.characters:[]; Rectangle { width:parent.width; height:72; radius:Theme.radius.medium; color:Theme.colors.surface2; border.color:Theme.colors.border; RowLayout { anchors.fill:parent; anchors.margins:Theme.spacing.md; ColumnLayout { Layout.fillWidth:true; Text { text:modelData.name; color:Theme.colors.textPrimary; font.weight:Theme.type.semibold }; Text { text:(modelData.role||"other").replace(/_/g," "); color:Theme.colors.textMuted } }; IconButton { iconName:"trash"; tooltip:"Remove character assignment metadata"; onClicked:root.controller.deleteCharacter(modelData.id) } } } } } }
        InfoBanner { Layout.fillWidth:true; text:"Choose the project narrator or section voice overrides in Voice Studio. Story Studio never generates or clones voices automatically." }
    }
}
