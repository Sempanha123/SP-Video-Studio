import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
Item { id:root; property var controller; signal navigateRequested(string mode)
    ColumnLayout { anchors.fill:parent; spacing:Theme.spacing.md
        SectionHeader { title:"Story Script"; subtitle:"Each Story beat maps to a normal Script section. Manual script edits are preserved and changed beats are marked Source Changed." }
        AppCard { Layout.fillWidth:true; implicitHeight:170; ColumnLayout { anchors.fill:parent; anchors.margins:Theme.spacing.lg; spacing:Theme.spacing.md
            Text { text:"Beat → ScriptSection"; color:Theme.colors.textPrimary; font.pixelSize:Theme.type.heading; font.weight:Theme.type.semibold }
            Text { Layout.fillWidth:true; wrapMode:Text.WordWrap; text:"Create the first Story script from the outline, then continue writing in the existing Script Editor. Sync never silently overwrites changed user text."; color:Theme.colors.textSecondary }
            RowLayout { SecondaryButton { text:"Sync with Outline"; onClicked:if(root.controller)root.controller.syncScript() }; AppButton { text:"Create Script"; onClicked:if(root.controller)root.controller.createScript(false) }; SecondaryButton { text:"Open Script Editor"; onClicked:root.navigateRequested("script") } }
        } }
    }
}
