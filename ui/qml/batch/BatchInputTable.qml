import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
Item { id: root; property var controller; signal nextRequested()
    ColumnLayout { anchors.fill: parent; spacing: Theme.spacing.md
        RowLayout { Layout.fillWidth: true
            Text { text:"2. Data"; color:Theme.colors.textPrimary; font.pixelSize:Theme.type.titleMedium; font.weight:Theme.type.semibold }
            Item { Layout.fillWidth:true }
            AppButton { text:"Import CSV / JSON"; variant:"secondary"; compact:true; onClicked:fileHint.visible=!fileHint.visible }
        }
        AppTextField { id:fileHint; visible:false; Layout.fillWidth:true; placeholderText:"Paste a local CSV/JSON/JSONL file path, then press Enter"; onAccepted: root.controller.importInput(text) }
        SearchField { Layout.fillWidth:true; placeholderText:"Search input rows"; onTextChanged: if(root.controller) root.controller.setInputSearch(text) }
        Text { text:(root.controller ? root.controller.inputRows.length : 0)+" visible rows · uncheck rows you do not want to generate"; color:Theme.colors.textSecondary }
        ListView { Layout.fillWidth:true; Layout.fillHeight:true; clip:true; reuseItems:true; cacheBuffer:440; model:root.controller ? root.controller.inputRows : []
            Accessible.role: Accessible.List
            Accessible.name: "Batch input rows"
            delegate: Rectangle { width:ListView.view.width; height:Math.max(44,Math.round(44*Theme.textScale)); color:index%2?"transparent":Theme.colors.surfaceRaised
                Accessible.role: Accessible.ListItem
                Accessible.name: "Row " + String(modelData.rowIndex+1) + ". " + (modelData.validity || "valid")
                RowLayout { anchors.fill:parent; anchors.margins:8
                    CheckBox { Accessible.name:"Include batch row "+String(modelData.rowIndex+1); checked:modelData.selected!==false; onToggled: root.controller.setRowSelected(modelData.rowIndex,checked) }
                    Text { text:"#"+(modelData.rowIndex+1); color:Theme.colors.textSecondary; Layout.preferredWidth:50 }
                    Text { text:JSON.stringify(modelData.data); elide:Text.ElideRight; color:Theme.colors.textPrimary; Layout.fillWidth:true }
                    Text { text:modelData.validity || "valid"; color:Theme.colors.textSecondary; Layout.preferredWidth:70 }
                }
            }
        }
        AppButton { text:"Continue to Mapping"; enabled:root.controller && root.controller.inputRows.length>0; onClicked:root.nextRequested() }
    }
}
