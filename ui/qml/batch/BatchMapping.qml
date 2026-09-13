import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
Item { id:root; property var controller; property string templateId:""; property var mappings:[]; signal nextRequested()
    ColumnLayout { anchors.fill:parent; spacing:Theme.spacing.md
        Text { text:"3. Mapping"; color:Theme.colors.textPrimary; font.pixelSize:Theme.type.titleMedium; font.weight:Theme.type.semibold }
        Text { Layout.fillWidth:true; wrapMode:Text.WordWrap; color:Theme.colors.textSecondary; text:"Map Phase 24 placeholders to columns, fixed values, system values, reusable Assets or voices. Only safe predefined transforms are supported—no eval, Python, JavaScript or shell." }
        RowLayout { Layout.fillWidth:true
            AppButton { text:"Auto-map Columns"; accessibleName:"Auto-map matching columns"; onClicked:{ root.mappings=controller.suggestMappings(root.templateId); jsonMap.text=JSON.stringify(root.mappings,null,2) } }
            SecondaryButton { text:"Use Mapping JSON"; onClicked:{ try { root.mappings=JSON.parse(jsonMap.text || "[]") } catch(e) { root.mappings=[] } } }
            Text { text:root.mappings.length+" mappings"; color:Theme.colors.textSecondary }
        }
        TextArea { id:jsonMap; Accessible.name:"Batch mapping JSON"; Accessible.role:Accessible.EditableText; Layout.fillWidth:true; Layout.fillHeight:true; placeholderText:'[{"target":"headline","kind":"column","source":"headline","required":true}]'; wrapMode:TextArea.Wrap }
        AppButton { text:"Continue to Variants"; onClicked:{ try { root.mappings=JSON.parse(jsonMap.text || JSON.stringify(root.mappings)) } catch(e) {} root.nextRequested() } }
    }
}
